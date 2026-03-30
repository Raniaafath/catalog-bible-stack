import threading
import time
import traceback
from typing import Dict, Any

from django.conf import settings
from django.db.models import Count, Max, IntegerField, Sum, Subquery, OuterRef
from django.db.models.functions import Coalesce
from django.db.models import Value
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

# In-memory job tracker for background AI mapping tasks.
# Keyed by run_id (int). Values: {"status": "running|done|error", "result": {}, "error": str, "started_at": float}
_mapping_jobs: Dict[int, Dict[str, Any]] = {}

from api.v1.serializers import (
    KeywordSerializer,
    MetricSerializer,
    PlannerRunCreateSerializer,
    PlannerRunKeywordSerializer,
    PlannerRunSerializer,
    PlannerSeedSerializer,
)
from api.v1.serializers.keywords import (
    KeywordPlannerRunImportCsvSerializer,
    RunAttributeMapSerializer,
    RunAttributeMapUpdateSerializer,
    ProductKeywordMapSerializer,
)
from content.models import Locale, ProductHookTerm, ProductTypeSynonym
from content.models import SynonymStatus
from django.db.models import Q
from kw.models import (
    AttributeMap,
    Keyword,
    KeywordStatus,
    Metric,
    PlannerRun,
    PlannerRunKeyword,
    PlannerSeed,
    ProductKeywordMap,
    Source,
)
from catalog.models import Product, ProductTypeAttribute, Variant
from kw.services.csv_import import import_keywords_csv
from kw.services.mapping_service import run_rules_mapping
from kw.services.product_keyword_mapper import persist_product_keyword_maps
from kw.services.seed_builder import _normalize
from pub.services.ai_constants import DEFAULT_MAPPING_AI_MODEL, MAPPING_AI_MODELS
from kw.services.term_extraction import (
    extract_suggested_head_terms,
    extract_suggested_hook_terms,
    generate_head_term_meanings_en,
    generate_term_reasons,
)
from pub.models import Channel


class PlannerRunViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = (
        PlannerRun.objects.select_related("source", "locale", "product_type", "channel")
        .annotate(keyword_count=Count("run_keywords"))
        .order_by("-id")
    )
    serializer_class = PlannerRunSerializer


class PlannerRunKeywordViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PlannerRunKeyword.objects.select_related("keyword", "run").order_by("-id")
    serializer_class = PlannerRunKeywordSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        run_id = self.request.query_params.get("run_id")
        if run_id:
            try:
                queryset = queryset.filter(run_id=int(run_id))
            except (ValueError, TypeError):
                pass  # Invalid run_id, return all
        return queryset


class PlannerSeedViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PlannerSeed.objects.select_related("locale", "product_type", "channel").order_by("-id")
    serializer_class = PlannerSeedSerializer


class KeywordViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Keyword.objects.select_related("locale").order_by("-id")
    serializer_class = KeywordSerializer


class MetricViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Metric.objects.select_related("keyword", "source").order_by("-id")
    serializer_class = MetricSerializer


class KeywordPlannerRunCreateView(APIView):
    def post(self, request):
        serializer = PlannerRunCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        source, _ = Source.objects.get_or_create(code=data["source_code"])
        channel = Channel.objects.filter(code=data.get("channel_code"), is_active=True).first()

        run = PlannerRun.objects.create(
            source=source,
            locale_id=Locale.objects.get(code=data["locale_code"]).id,
            product_type_id=data.get("product_type_id"),
            channel=channel,
            request_json={
                "seed_terms": data.get("seed_terms", []),
                "negative_terms": data.get("negative_terms", []),
            },
            status=PlannerRun.Status.QUEUED,
        )

        seed_terms = data.get("seed_terms", [])
        if seed_terms:
            for term in seed_terms:
                norm = _normalize(term)
                seed, _ = PlannerSeed.objects.get_or_create(
                    locale_id=run.locale_id,
                    product_type_id=run.product_type_id,
                    channel_id=run.channel_id,
                    normalized_term=norm,
                    defaults={
                        "term": term,
                        "seed_type": PlannerSeed.SeedType.CATEGORY,
                    },
                )
                PlannerRunKeyword.objects.get_or_create(
                    run=run,
                    keyword=Keyword.objects.get_or_create(
                        locale_id=run.locale_id,
                        normalized_term=norm,
                        defaults={"term": term},
                    )[0],
                    seed=seed,
                )

        return Response({"run_id": run.id, "status": run.status}, status=status.HTTP_201_CREATED)


class KeywordPlannerRunImportCsvView(APIView):
    def post(self, request):
        csv_file = request.FILES.get("file")
        if not csv_file:
            return Response(
                {"detail": "Missing file. Use form field 'file' for the CSV upload."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        params = {
            "locale_code": request.data.get("locale_code", "").strip(),
            "channel_code": request.data.get("channel_code", "").strip(),
            "source_code": (request.data.get("source_code") or "google_ads").strip(),
            "month": request.data.get("month") or "",
            "delimiter": (request.data.get("delimiter") or ",").strip() or ",",
        }
        run_id = request.data.get("run_id")
        if run_id is not None and run_id != "":
            try:
                params["run_id"] = int(run_id)
            except (TypeError, ValueError):
                params["run_id"] = None
        else:
            params["run_id"] = None
        product_type_id = request.data.get("product_type_id")
        if product_type_id is not None and product_type_id != "":
            try:
                params["product_type_id"] = int(product_type_id)
            except (TypeError, ValueError):
                params["product_type_id"] = None
        else:
            params["product_type_id"] = None

        serializer = KeywordPlannerRunImportCsvSerializer(data=params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            result = import_keywords_csv(
                file=csv_file,
                locale_code=data["locale_code"],
                channel_code=data["channel_code"],
                source_code=data.get("source_code", "google_ads"),
                run_id=data.get("run_id"),
                product_type_id=data.get("product_type_id"),
                month_str=data.get("month") or None,
                delimiter=data.get("delimiter", ","),
            )
        except (Locale.DoesNotExist, Channel.DoesNotExist) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {
                    "detail": str(e),
                    "error_type": type(e).__name__,
                    "traceback": traceback.format_exc(),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(result, status=status.HTTP_201_CREATED)


class KeywordPlannerRunDetailView(APIView):
    def get(self, request, run_id: int):
        run = (
            PlannerRun.objects.select_related("locale", "channel", "product_type")
            .annotate(keyword_count=Count("run_keywords"))
            .get(id=run_id)
        )
        run_keywords = PlannerRunKeyword.objects.filter(run=run).select_related("keyword")

        metrics = (
            Metric.objects.filter(keyword_id__in=run_keywords.values_list("keyword_id", flat=True))
            .values("keyword_id")
            .annotate(avg_searches=Max("avg_searches"), competition=Max("competition"), cpc=Max("cpc"))
        )
        metric_map = {m["keyword_id"]: m for m in metrics}

        keywords_payload = []
        for prk in run_keywords:
            metric = metric_map.get(prk.keyword_id, {})
            comp = metric.get("competition")
            if comp is not None:
                try:
                    comp_float = float(comp)
                    if comp_float < 0.33:
                        competition_label = "low"
                    elif comp_float < 0.66:
                        competition_label = "medium"
                    else:
                        competition_label = "high"
                except (TypeError, ValueError):
                    competition_label = str(comp) if comp else None
            else:
                competition_label = None
            keywords_payload.append(
                {
                    "id": prk.id,
                    "keyword_id": prk.keyword_id,
                    "keyword": prk.keyword.term,
                    "term": prk.keyword.term,
                    "status": prk.status,
                    "approved": prk.status == KeywordStatus.APPROVED,
                    "concept": prk.concept,
                    "avg_searches": metric.get("avg_searches"),
                    "search_volume": metric.get("avg_searches"),
                    "competition": competition_label,
                    "cpc": metric.get("cpc"),
                }
            )

        response = {
            "run": PlannerRunSerializer(run).data,
            "keywords": keywords_payload,
        }
        return Response(response, status=status.HTTP_200_OK)


class KeywordPlannerRunApproveView(APIView):
    def post(self, request, run_id: int):
        keyword_ids = request.data.get("keyword_ids", [])
        if not keyword_ids:
            return Response({"detail": "keyword_ids is required."}, status=status.HTTP_400_BAD_REQUEST)
        PlannerRunKeyword.objects.filter(run_id=run_id, keyword_id__in=keyword_ids).update(
            status=KeywordStatus.APPROVED
        )
        return Response({"updated": len(keyword_ids)}, status=status.HTTP_200_OK)


class KeywordPlannerRunMapView(APIView):
    """POST: run rules-based keyword mapping for this run."""

    def post(self, request, run_id: int):
        limit = request.data.get("limit")
        if limit is not None:
            try:
                limit = int(limit)
            except (TypeError, ValueError):
                limit = 500
        else:
            limit = 500
        dry_run = request.data.get("dry_run", False)
        result = run_rules_mapping(run_id, limit=limit, dry_run=dry_run)
        if result.get("error"):
            return Response({"detail": result["error"]}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class KeywordPlannerRunMappingsView(APIView):
    """GET: list attribute mappings for this run (paginated, filterable, sortable)."""

    _SORT_FIELDS = {
        "keyword": "keyword__term",
        "attribute": "attribute__code",
        "value": "attribute_value__code",
        "confidence": "confidence",
        "status": "status",
    }

    def get(self, request, run_id: int):
        page = int(request.query_params.get("page", 1))
        page_size = min(int(request.query_params.get("page_size", 50)), 100)
        status_filter = request.query_params.get("status", "").strip().lower()
        sort_by = request.query_params.get("sort_by", "keyword").strip().lower()
        sort_dir = request.query_params.get("sort_dir", "asc").strip().lower()

        offset = (page - 1) * page_size
        qs = (
            AttributeMap.objects.filter(origin_run_keyword__run_id=run_id)
            .select_related("keyword", "attribute", "attribute_value")
        )

        # Server-side status filter
        if status_filter in ("suggested", "approved", "rejected"):
            qs = qs.filter(status=status_filter)

        # Sorting
        order_field = self._SORT_FIELDS.get(sort_by, "keyword__term")
        if sort_dir == "desc":
            order_field = f"-{order_field}"
        qs = qs.order_by(order_field, "keyword__term", "attribute__code")

        total = qs.count()
        items = qs[offset: offset + page_size]
        serializer = RunAttributeMapSerializer(items, many=True)
        return Response(
            {
                "count": total,
                "next": f"?page={page + 1}&page_size={page_size}" if offset + page_size < total else None,
                "previous": f"?page={page - 1}&page_size={page_size}" if page > 1 else None,
                "results": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class KeywordPlannerRunMappingDetailView(APIView):
    """PATCH: update a single attribute mapping status (approved/rejected)."""

    def patch(self, request, attribute_map_id: int):
        serializer = RunAttributeMapUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        updated = AttributeMap.objects.filter(id=attribute_map_id).update(status=data["status"])
        if not updated:
            return Response({"detail": "AttributeMap not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"status": data["status"]}, status=status.HTTP_200_OK)


class KeywordPlannerRunMappingsBulkUpdateView(APIView):
    """POST: bulk approve or reject all (or filtered) attribute mappings for a run."""

    def post(self, request, run_id: int):
        action = (request.data.get("action") or "").strip().lower()
        if action not in ("approve", "reject"):
            return Response(
                {"detail": "action must be 'approve' or 'reject'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        new_status = AttributeMap.Status.APPROVED if action == "approve" else AttributeMap.Status.REJECTED

        # Optional filters
        current_status = (request.data.get("status") or "").strip().lower()
        attribute_code = (request.data.get("attribute_code") or "").strip()
        ids = request.data.get("ids")  # optional list of specific IDs

        qs = AttributeMap.objects.filter(origin_run_keyword__run_id=run_id)
        if ids and isinstance(ids, list):
            qs = qs.filter(id__in=ids)
        else:
            if current_status in ("suggested", "approved", "rejected"):
                qs = qs.filter(status=current_status)
            if attribute_code:
                qs = qs.filter(attribute__code=attribute_code)

        updated = qs.update(status=new_status)
        return Response({"updated": updated, "action": action}, status=status.HTTP_200_OK)


class KeywordPlannerRunMappingsClearAllView(APIView):
    """
    GET  /keywords/planner-run/{run_id}/mappings/clear-all/
        Returns count of attribute mappings that would be deleted (preview).
    DELETE /keywords/planner-run/{run_id}/mappings/clear-all/
        Body: {"confirm": true}
        Deletes all AttributeMap rows for this run.
    """

    def get(self, request, run_id: int):
        if not PlannerRun.objects.filter(id=run_id).exists():
            return Response({"detail": "Run not found."}, status=status.HTTP_404_NOT_FOUND)
        count = AttributeMap.objects.filter(origin_run_keyword__run_id=run_id).count()
        return Response({"run_id": run_id, "count": count}, status=status.HTTP_200_OK)

    def delete(self, request, run_id: int):
        if not PlannerRun.objects.filter(id=run_id).exists():
            return Response({"detail": "Run not found."}, status=status.HTTP_404_NOT_FOUND)
        confirm = request.data.get("confirm")
        if confirm is not True:
            return Response(
                {"detail": "Send {\"confirm\": true} to proceed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        deleted, _ = AttributeMap.objects.filter(origin_run_keyword__run_id=run_id).delete()
        return Response({"run_id": run_id, "deleted": deleted}, status=status.HTTP_200_OK)


class KeywordPlannerRunPersistMappingsView(APIView):
    """
    POST: persist per-product keyword mappings (with optional LLM).
    Pass async_job=true to run in the background and poll via GET for status.
    GET: return current background job status for this run_id.
    """

    def get(self, request, run_id: int):
        job = _mapping_jobs.get(run_id)
        if not job:
            return Response(
                {"run_id": run_id, "job_status": "idle"},
                status=status.HTTP_200_OK,
            )
        return Response(
            {
                "run_id": run_id,
                "job_status": job["status"],
                "result": job.get("result"),
                "error": job.get("error"),
                "started_at": job.get("started_at"),
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request, run_id: int):
        try:
            product_id = request.data.get("product_id")
            limit = request.data.get("limit")
            min_confidence = request.data.get("min_confidence")
            include_text_values = request.data.get("include_text_values", True)
            include_i18n = request.data.get("include_i18n", True)
            include_descriptions = request.data.get("include_descriptions", False)
            max_description_chars = request.data.get("max_description_chars", 2000)
            max_text_matches = request.data.get("max_text_matches", 60)
            max_enum_maps = request.data.get("max_enum_maps", 120)
            use_llm = request.data.get("use_llm", False)
            llm_model = (request.data.get("llm_model") or "").strip() or DEFAULT_MAPPING_AI_MODEL
            if llm_model not in MAPPING_AI_MODELS:
                return Response(
                    {"detail": f"Unknown llm_model '{llm_model}'. Allowed: {sorted(MAPPING_AI_MODELS)}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            llm_max_keywords = request.data.get("llm_max_keywords", 80)
            dry_run = request.data.get("dry_run", False)
            focus_on = (request.data.get("focus_on") or "").strip() or None
            ignore = (request.data.get("ignore") or "").strip() or None
            ignore_size_and_marketplace = request.data.get("ignore_size_and_marketplace", False) is True
            focus_head_terms = request.data.get("focus_head_terms", False) is True
            focus_hook_terms = request.data.get("focus_hook_terms", False) is True
            skip_enum_maps = request.data.get("skip_enum_maps", False) is True
            async_job = request.data.get("async_job", False) is True

            kwargs = dict(
                run_id=run_id,
                product_id=product_id,
                limit=limit,
                min_confidence=min_confidence,
                include_text_values=include_text_values,
                include_i18n=include_i18n,
                include_descriptions=include_descriptions,
                max_description_chars=max_description_chars,
                max_text_matches=max_text_matches,
                max_enum_maps=max_enum_maps,
                use_llm=use_llm,
                llm_model=llm_model,
                llm_max_keywords=llm_max_keywords,
                dry_run=dry_run,
                focus_on=focus_on,
                ignore=ignore,
                ignore_size_and_marketplace=ignore_size_and_marketplace,
                focus_head_terms=focus_head_terms,
                focus_hook_terms=focus_hook_terms,
                skip_enum_maps=skip_enum_maps,
            )

            if async_job:
                if _mapping_jobs.get(run_id, {}).get("status") == "running":
                    return Response(
                        {"run_id": run_id, "job_status": "running", "detail": "Job already running."},
                        status=status.HTTP_200_OK,
                    )
                _mapping_jobs[run_id] = {"status": "running", "started_at": time.time(), "result": None, "error": None}

                def _run():
                    try:
                        result = persist_product_keyword_maps(**kwargs)
                        _mapping_jobs[run_id]["status"] = "done"
                        _mapping_jobs[run_id]["result"] = result
                    except Exception as exc:
                        _mapping_jobs[run_id]["status"] = "error"
                        _mapping_jobs[run_id]["error"] = str(exc)

                thread = threading.Thread(target=_run, daemon=True)
                thread.start()
                return Response({"run_id": run_id, "job_status": "running"}, status=status.HTTP_202_ACCEPTED)

            result = persist_product_keyword_maps(**kwargs)
            return Response(result)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            payload = {"error": str(e)}
            if getattr(settings, "DEBUG", False):
                payload["detail"] = traceback.format_exc()
            return Response(payload, status=status.HTTP_500_INTERNAL_SERVER_ERROR, content_type="application/json")


class KeywordPlannerRunSuggestedTermsView(APIView):
    """
    GET: Extract suggested head terms (product type) and hook terms (for a product)
    from this run's ProductKeywordMap. Used after mapping so the user can approve/deny.
    Query params: product_id (required for hook terms), locale_id (required), channel_id (optional).
    Approve head term: POST /product-types/{id}/head-terms/ with { locale_id, channel_id?, term }.
    Approve hook term: POST /products/{id}/hook-terms/ with { locale_id, channel_id?, term, priority? }.
    """

    def get(self, request, run_id: int):
        run = PlannerRun.objects.select_related("locale", "product_type", "channel").filter(id=run_id).first()
        if not run:
            return Response({"detail": "Run not found."}, status=status.HTTP_404_NOT_FOUND)
        locale_id = request.query_params.get("locale_id")
        if not locale_id:
            return Response({"detail": "locale_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            locale_id = int(locale_id)
        except (TypeError, ValueError):
            return Response({"detail": "locale_id must be an integer."}, status=status.HTTP_400_BAD_REQUEST)
        channel_id = request.query_params.get("channel_id")
        if channel_id is not None:
            try:
                channel_id = int(channel_id)
            except (TypeError, ValueError):
                channel_id = None
        product_id = request.query_params.get("product_id")
        if product_id is not None:
            try:
                product_id = int(product_id)
            except (TypeError, ValueError):
                product_id = None

        max_head_terms = request.query_params.get("max_head_terms")
        max_hook_terms = request.query_params.get("max_hook_terms")
        try:
            max_head_terms = int(max_head_terms) if max_head_terms not in (None, "") else 20
            max_head_terms = max(1, min(max_head_terms, 100))
        except (TypeError, ValueError):
            max_head_terms = 20
        try:
            max_hook_terms = int(max_hook_terms) if max_hook_terms not in (None, "") else 30
            max_hook_terms = max(1, min(max_hook_terms, 200))
        except (TypeError, ValueError):
            max_hook_terms = 30

        suggested_head = extract_suggested_head_terms(
            run=run,
            locale_id=locale_id,
            channel_id=channel_id,
            max_terms=max_head_terms,
        )
        head_norm = set()
        from kw.management.commands.parse_keywords import _normalize_term
        for h in suggested_head:
            t = (h.get("term") or "").strip()
            if t:
                head_norm.add(_normalize_term(t))

        suggested_hook = []
        if product_id:
            if not Product.objects.filter(id=product_id).exists():
                return Response({"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND)
            suggested_hook = extract_suggested_hook_terms(
                run=run,
                product_id=product_id,
                locale_id=locale_id,
                channel_id=channel_id,
                head_terms_normalized=head_norm,
                max_terms=max_hook_terms,
            )
        else:
            product_ids = list(
                ProductKeywordMap.objects.filter(run=run)
                .values_list("product_id", flat=True)
                .distinct()
            )
            # Fetch up to 10 hooks per product so each product is represented.
            # Then round-robin across products (best hook per product first) to
            # build the final list, so volume from a few products doesn't drown out others.
            per_product_fetch = 10
            per_product_hooks: Dict[int, list] = {}
            for pid in product_ids[:50]:
                hook_list = extract_suggested_hook_terms(
                    run=run,
                    product_id=pid,
                    locale_id=locale_id,
                    channel_id=channel_id,
                    head_terms_normalized=head_norm,
                    max_terms=per_product_fetch,
                )
                if hook_list:
                    per_product_hooks[pid] = hook_list
            # Round-robin: take 1 hook per product in volume-desc order until max_hook_terms
            all_hook = []
            round_idx = 0
            product_queues = list(per_product_hooks.values())
            while len(all_hook) < max_hook_terms and any(len(q) > round_idx for q in product_queues):
                for q in product_queues:
                    if round_idx < len(q):
                        all_hook.append(q[round_idx])
                    if len(all_hook) >= max_hook_terms:
                        break
                round_idx += 1
            suggested_hook = all_hook

        product_ids_in_hook = list({h["product_id"] for h in suggested_hook})
        product_variants = {}
        if product_ids_in_hook:
            for v in Variant.objects.filter(product_id__in=product_ids_in_hook).order_by("product_id", "id").values(
                "id", "product_id", "sku", "source_title"
            ):
                pid = v["product_id"]
                if pid not in product_variants:
                    product_variants[pid] = []
                product_variants[pid].append(
                    {
                        "id": v["id"],
                        "sku": (v.get("sku") or "").strip() or None,
                        "source_title": (v.get("source_title") or "").strip() or None,
                    }
                )

        run_product_type = getattr(run, "product_type", None)
        product_type_default_label = (
            (getattr(run_product_type, "default_label", None) or "").strip() or None
        ) if run_product_type else None
        product_type_notes = (
            (getattr(run_product_type, "notes", None) or "").strip() or None
        ) if run_product_type else None
        product_type_main_category = (
            (getattr(run_product_type, "main_category", None) or "").strip() or None
        ) if run_product_type else None

        use_ai_meaning = request.query_params.get("use_ai_meaning", "").lower() in ("1", "true", "yes")
        if use_ai_meaning and suggested_head:
            meanings_en = generate_head_term_meanings_en(
                suggested_head,
                product_type_label=product_type_default_label,
                product_type_code=getattr(run_product_type, "code", None) if run_product_type else None,
            )
            for i, h in enumerate(suggested_head):
                h["meaning_en"] = meanings_en[i] if i < len(meanings_en) else None

        use_ai_reason = request.query_params.get("use_ai_reason", "").lower() in ("1", "true", "yes")
        if use_ai_reason and (suggested_head or suggested_hook):
            head_reasons, hook_reasons = generate_term_reasons(
                suggested_head,
                suggested_hook,
                product_type_label=product_type_default_label,
                product_type_code=getattr(run_product_type, "code", None) if run_product_type else None,
            )
            for i, h in enumerate(suggested_head):
                h["reason"] = head_reasons[i] if i < len(head_reasons) else None
            for i, h in enumerate(suggested_hook):
                if not (h.get("reason") or "").strip():
                    h["reason"] = hook_reasons[i] if i < len(hook_reasons) else None

        return Response({
            "run_id": run.id,
            "product_type_id": run.product_type_id,
            "product_type_code": getattr(run_product_type, "code", None) if run_product_type else None,
            "product_type_default_label": product_type_default_label,
            "product_type_notes": product_type_notes,
            "product_type_main_category": product_type_main_category,
            "product_id": product_id,
            "locale_id": locale_id,
            "channel_id": channel_id,
            "max_head_terms": max_head_terms,
            "max_hook_terms": max_hook_terms,
            "suggested_head_terms": suggested_head,
            "suggested_hook_terms": suggested_hook,
            "product_variants": product_variants,
            "approve_head_url": f"/api/v1/product-types/{run.product_type_id}/head-terms/" if run.product_type_id else None,
            "approve_hook_url": f"/api/v1/products/{product_id}/hook-terms/" if product_id else None,
        }, status=status.HTTP_200_OK)


class SavedTermsView(APIView):
    """
    GET: List saved head terms (by product type) and hook terms (by product) for a locale and optional channel.
    Query params: locale_id (required for terms), channel_id (optional).
    When locale_id is omitted, returns only locales and channels for the filter UI.
    """

    def get(self, request):
        from content.models import ProductTypeI18n

        locales = list(
            Locale.objects.order_by("code").values("id", "code", "name")
        )
        channels = list(
            Channel.objects.order_by("code").values("id", "code", "name")
        )
        locale_id = request.query_params.get("locale_id")
        channel_id = request.query_params.get("channel_id")

        if not locale_id:
            return Response({
                "locales": locales,
                "channels": channels,
                "head_terms_by_product_type": [],
                "hook_terms_by_product": [],
            })

        try:
            locale = Locale.objects.get(id=locale_id)
        except Locale.DoesNotExist:
            return Response(
                {"detail": "Locale not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        channel = Channel.objects.filter(id=channel_id).first() if channel_id else None

        # Head terms: ProductTypeSynonym (approved, active) + ProductTypeI18n label, grouped by product type
        syn_qs = (
            ProductTypeSynonym.objects.filter(
                locale=locale,
                status=SynonymStatus.APPROVED,
                is_active=True,
            )
            .select_related("product_type")
            .order_by("product_type_id", "-priority", "id")
        )
        if channel:
            syn_qs = syn_qs.filter(Q(channel=channel) | Q(channel__isnull=True))

        head_by_pt: dict = {}
        for syn in syn_qs:
            pt_id = syn.product_type_id
            if pt_id not in head_by_pt:
                head_by_pt[pt_id] = {
                    "product_type_id": pt_id,
                    "product_type_code": syn.product_type.code if syn.product_type else None,
                    "default_label": getattr(syn.product_type, "default_label", "") or "",
                    "terms": [],
                }
            head_by_pt[pt_id]["terms"].append({
                "id": syn.id,
                "term": syn.term,
                "source": "synonym",
            })

        # Prepend product-type label as first term where available
        pt_ids_with_synonyms = set(head_by_pt.keys())
        pti18n = ProductTypeI18n.objects.filter(
            product_type_id__in=pt_ids_with_synonyms,
            locale=locale,
        ).exclude(label="")
        for pti in pti18n:
            if pti.product_type_id in head_by_pt:
                head_by_pt[pti.product_type_id]["terms"].insert(
                    0, {"id": None, "term": pti.label, "source": "label"}
                )

        head_terms_by_product_type = list(head_by_pt.values())
        head_terms_by_product_type.sort(
            key=lambda x: (x["product_type_code"] or "", x["default_label"] or "")
        )

        # Hook terms: ProductHookTerm, grouped by product
        hook_qs = (
            ProductHookTerm.objects.filter(locale=locale)
            .select_related("product")
            .order_by("product_id", "-priority", "id")
        )
        if channel:
            hook_qs = hook_qs.filter(Q(channel=channel) | Q(channel__isnull=True))

        hook_by_product: dict = {}
        for h in hook_qs:
            pid = h.product_id
            if pid not in hook_by_product:
                hook_by_product[pid] = {
                    "product_id": pid,
                    "product_code": h.product.code if h.product else None,
                    "default_label": (h.product.default_label or "").strip() if h.product else "",
                    "terms": [],
                }
            hook_by_product[pid]["terms"].append({
                "id": h.id,
                "term": h.term,
                "priority": h.priority,
            })

        hook_terms_by_product = list(hook_by_product.values())
        hook_terms_by_product.sort(
            key=lambda x: (x["product_code"] or "", x["default_label"] or "")
        )

        return Response({
            "locales": locales,
            "channels": channels,
            "head_terms_by_product_type": head_terms_by_product_type,
            "hook_terms_by_product": hook_terms_by_product,
        })


class KeywordPlannerRunProductMapsView(APIView):
    """
    GET endpoint to retrieve ProductKeywordMaps for a run.
    """

    def get(self, request, run_id: int):
        page = int(request.query_params.get("page", 1))
        page_size = min(int(request.query_params.get("page_size", 50)), 100)
        product_id = request.query_params.get("product_id")
        source = request.query_params.get("source")
        
        offset = (page - 1) * page_size
        qs = (
            ProductKeywordMap.objects.filter(run_id=run_id)
            .select_related("keyword", "product", "attribute", "attribute_value")
            .order_by("product_id", "keyword__term")
        )
        
        if product_id:
            qs = qs.filter(product_id=product_id)
        if source:
            qs = qs.filter(source=source)
            
        total = qs.count()
        items = qs[offset : offset + page_size]
        serializer = ProductKeywordMapSerializer(items, many=True)

        return Response(
            {
                "count": total,
                "next": f"?page={page + 1}&page_size={page_size}" if offset + page_size < total else None,
                "previous": f"?page={page - 1}&page_size={page_size}" if page > 1 else None,
                "results": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class KeywordPlannerRunProductMapDetailView(APIView):
    """
    DELETE a single ProductKeywordMap (must belong to the given run).
    """

    def delete(self, request, run_id: int, map_id: int):
        obj = ProductKeywordMap.objects.filter(id=map_id, run_id=run_id).first()
        if not obj:
            return Response(
                {"detail": "Product keyword map not found or does not belong to this run."},
                status=status.HTTP_404_NOT_FOUND,
            )
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class KeywordPlannerRunProductMapsClearAllView(APIView):
    """
    DANGEROUS: Delete ALL ProductKeywordMaps for a planner run.

    GET  /keywords/planner-run/{run_id}/product-maps/clear-all/
        Returns a count of mappings that would be deleted (preview, no changes).

    DELETE /keywords/planner-run/{run_id}/product-maps/clear-all/
        Body: {"confirm": true}
        Deletes all ProductKeywordMap rows for this run.
        Returns {"deleted": int, "run_id": int}.
    """

    def get(self, request, run_id: int):
        if not PlannerRun.objects.filter(id=run_id).exists():
            return Response({"detail": "Run not found."}, status=status.HTTP_404_NOT_FOUND)
        count = ProductKeywordMap.objects.filter(run_id=run_id).count()
        return Response({"run_id": run_id, "count": count}, status=status.HTTP_200_OK)

    def delete(self, request, run_id: int):
        confirm = request.data.get("confirm")
        if confirm is not True:
            return Response(
                {
                    "detail": (
                        "This will delete all keyword mappings for this run. "
                        "Send {\"confirm\": true} to proceed."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not PlannerRun.objects.filter(id=run_id).exists():
            return Response({"detail": "Run not found."}, status=status.HTTP_404_NOT_FOUND)
        deleted, _ = ProductKeywordMap.objects.filter(run_id=run_id).delete()
        return Response({"run_id": run_id, "deleted": deleted}, status=status.HTTP_200_OK)


class KeywordPlannerRunProposeTemplateView(APIView):
    """
    GET /keywords/planner-run/{run_id}/propose-template/

    Returns attributes ordered by total mapped keyword search volume for this run.
    Optionally asks an AI to reorder / annotate them with semantic reasoning.

    Query params:
        top (int, default 8): maximum number of attributes to return
        use_ai (0/1, default 0): ask AI to reorder and add a reason per attribute

    Response:
        {
            "run_id": 12,
            "source": "volume" | "ai",
            "proposed": [
                {
                    "attribute_id": 5,
                    "attribute_code": "couleur",
                    "total_vol": 45000,
                    "keyword_count": 12,
                    "reason": "Colour is the primary differentiator buyers use in searches."
                },
                ...
            ]
        }
    """

    def get(self, request, run_id: int):
        import json, os
        run = PlannerRun.objects.select_related("product_type", "locale").filter(id=run_id).first()
        if not run:
            return Response({"detail": "Run not found."}, status=status.HTTP_404_NOT_FOUND)

        top = int(request.query_params.get("top", 8))
        use_ai = request.query_params.get("use_ai", "").lower() in ("1", "true", "yes")

        # ── Step 1: volume-based ranking ─────────────────────────────────────
        kw_vol_sq = (
            Metric.objects.filter(keyword_id=OuterRef("keyword_id"))
            .values("keyword_id")
            .annotate(v=Max("avg_searches"))
            .values("v")[:1]
        )

        rows = (
            ProductKeywordMap.objects.filter(run=run, attribute__isnull=False, attribute__use_in_title=True)
            .annotate(kw_vol=Subquery(kw_vol_sq, output_field=IntegerField()))
            .values("attribute_id", "attribute__code", "attribute__data_type", "attribute__unit")
            .annotate(
                total_vol=Sum(Coalesce("kw_vol", Value(0))),
                keyword_count=Count("keyword_id", distinct=True),
            )
            .order_by("-total_vol")[:top]
        )

        proposed = [
            {
                "attribute_id": r["attribute_id"],
                "attribute_code": r["attribute__code"],
                "data_type": r["attribute__data_type"],
                "unit": r["attribute__unit"],
                "total_vol": r["total_vol"] or 0,
                "keyword_count": r["keyword_count"],
                "reason": None,
            }
            for r in rows
        ]

        # ── Identify fixed axis attributes (variant_level=True) ──────────────
        # These are always position 2 in the title (after head term).
        # They are excluded from the AI candidate list.
        axis_attr_codes: set = set()
        axis_attributes = []
        if run.product_type:
            for pta in ProductTypeAttribute.objects.filter(
                product_type=run.product_type, variant_level=True
            ).select_related("attribute").order_by("id"):
                axis_attr_codes.add(pta.attribute.code)
                axis_attributes.append({
                    "attribute_id": pta.attribute.id,
                    "attribute_code": pta.attribute.code,
                    "fixed": True,
                    "reason": None,
                })

        # Remove axis attributes from the candidate list — they have a fixed slot
        proposed = [p for p in proposed if p["attribute_code"] not in axis_attr_codes]

        if not proposed and not axis_attributes:
            return Response({"run_id": run_id, "source": "volume", "axis_attributes": [], "proposed": []})

        # ── Step 2: AI reorder + reasons ─────────────────────────────────────
        if use_ai:
            pt = run.product_type
            pt_label = (getattr(pt, "default_label", "") or "").strip() if pt else ""
            pt_code = (getattr(pt, "code", "") or "").strip() if pt else ""
            pt_category = (getattr(pt, "main_category", "") or "").strip() if pt else ""
            product_context = pt_label or pt_code or "product"
            if pt_category:
                product_context = f"{product_context} ({pt_category})"

            # Locale / language context
            locale_code = run.locale.code if run.locale_id else "en"  # e.g. "fr-FR"
            lang_name = {
                "fr": "French", "de": "German", "es": "Spanish", "it": "Italian",
                "pt": "Portuguese", "nl": "Dutch", "pl": "Polish", "en": "English",
                "ja": "Japanese", "zh": "Chinese", "ko": "Korean", "ar": "Arabic",
                "sv": "Swedish", "da": "Danish", "fi": "Finnish", "no": "Norwegian",
            }.get(locale_code.split("-")[0].lower(), locale_code)

            # Sample top keywords from the run for extra context
            sample_kws = list(
                ProductKeywordMap.objects.filter(run=run)
                .annotate(kw_vol=Subquery(kw_vol_sq, output_field=IntegerField()))
                .select_related("keyword")
                .order_by("-kw_vol")
                .values_list("keyword__term", flat=True)
                .distinct()[:25]
            )
            sample_kw_lines = ", ".join(f'"{t}"' for t in sample_kws if t)

            axis_label = ", ".join(a["attribute_code"] for a in axis_attributes) if axis_attributes else "none"

            attr_lines = "\n".join(
                f"{i+3}. {p['attribute_code']}"
                f"{' [' + p['data_type'] + ']' if p.get('data_type') else ''}"
                f"{' [unit: ' + p['unit'] + ']' if p.get('unit') else ''}"
                f" — {p['total_vol']:,} searches, {p['keyword_count']} keywords"
                for i, p in enumerate(proposed)
            ) if proposed else "(no additional candidates)"

            system_prompt = (
                "You are an e-commerce SEO expert who determines which product attributes to include "
                "in a marketplace title and in what order. "
                "You work across all product categories (furniture, electronics, fashion, food, toys, …) "
                "and all languages. "
                f"The target marketplace language is {lang_name} (locale: {locale_code}). "
                "Write your reasons in that language. "
                "The title always starts with: [head term] (position 1, fixed) then [variation axis] (position 2, fixed). "
                "Your job is to select and order the remaining attributes for positions 3 onwards. "
                "You may exclude attributes that add no buyer value for this product type. "
                "Do NOT add new attributes — only select and order from the ones provided. "
                "Return valid JSON only."
            )
            user_prompt = (
                f"Product type: {product_context}\n"
                f"Locale: {locale_code}\n\n"
                f"FIXED title structure (do NOT change these):\n"
                f"  Position 1: [head term] — product type label (e.g. '{product_context}')\n"
                f"  Position 2: [{axis_label}] — variation axis, always second\n\n"
                + (f"Top buyer search queries:\n{sample_kw_lines}\n\n" if sample_kw_lines else "")
                + f"Candidate attributes for positions 3+ (ranked by search volume):\n{attr_lines}\n\n"
                "Task: Select the most buyer-relevant attributes for positions 3+ and order them best-first. "
                "You may drop attributes that are redundant or low-value for this product type. "
                "Consider semantic flow: broad/defining attributes before narrow/specific ones.\n\n"
                'Return JSON: {"proposed": [{"attribute_code": "...", "reason": "..."}, ...]}'
            )

            raw: Optional[str] = None
            model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

            try:
                if model.startswith("claude-"):
                    api_key = os.environ.get("ANTHROPIC_API_KEY")
                    if api_key:
                        import anthropic
                        client = anthropic.Anthropic(api_key=api_key)
                        msg = client.messages.create(
                            model=model, max_tokens=900,
                            system=system_prompt,
                            messages=[{"role": "user", "content": user_prompt}],
                            temperature=0,
                        )
                        raw = msg.content[0].text if msg.content else None
                elif model.startswith("gemini-"):
                    api_key = os.environ.get("GOOGLE_AI_API_KEY")
                    if api_key:
                        import google.generativeai as genai
                        genai.configure(api_key=api_key)
                        g = genai.GenerativeModel(
                            model_name=model,
                            system_instruction=system_prompt,
                            generation_config={"temperature": 0, "max_output_tokens": 900, "response_mime_type": "application/json"},
                        )
                        raw = g.generate_content(user_prompt).text
                else:
                    api_key = os.environ.get("OPENAI_API_KEY")
                    if api_key:
                        from openai import OpenAI
                        client = OpenAI(api_key=api_key)
                        resp = client.chat.completions.create(
                            model=model, temperature=0, max_tokens=900,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                        )
                        raw = resp.choices[0].message.content or None
            except Exception:
                pass

            if raw:
                try:
                    data = json.loads(raw.strip())
                    ai_list = data.get("proposed") or []
                    # Rebuild proposed in AI order, preserving volume data
                    by_code = {p["attribute_code"]: p for p in proposed}
                    reordered = []
                    seen = set()
                    for item in ai_list:
                        code = (item.get("attribute_code") or "").strip()
                        # AI must not sneak in axis attributes
                        if code in by_code and code not in seen and code not in axis_attr_codes:
                            entry = dict(by_code[code])
                            entry["reason"] = (item.get("reason") or "").strip() or None
                            reordered.append(entry)
                            seen.add(code)
                    # Append any attributes AI omitted (keep volume order)
                    for p in proposed:
                        if p["attribute_code"] not in seen:
                            reordered.append(p)
                    proposed = reordered
                    # Clean internal fields before returning
                    for p in proposed:
                        p.pop("data_type", None)
                        p.pop("unit", None)
                    return Response({"run_id": run_id, "source": "ai", "axis_attributes": axis_attributes, "proposed": proposed})
                except Exception:
                    pass

        # Clean internal fields
        for p in proposed:
            p.pop("data_type", None)
            p.pop("unit", None)
        return Response({"run_id": run_id, "source": "volume", "axis_attributes": axis_attributes, "proposed": proposed})
