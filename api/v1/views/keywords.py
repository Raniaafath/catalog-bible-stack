import traceback

from django.conf import settings
from django.core.management import call_command
from django.db.models import Count, Max
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

import json
import time

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
from catalog.models import Product, Variant
from kw.services.csv_import import import_keywords_csv
from kw.services.mapping_service import run_rules_mapping
from kw.services.product_keyword_mapper import persist_product_keyword_maps
from kw.services.seed_builder import _normalize
from kw.services.term_extraction import (
    extract_suggested_head_terms,
    extract_suggested_hook_terms,
    generate_head_term_meanings_en,
)
from pub.models import Channel


def _agent_debug_log(hypothesis_id: str, location: str, message: str, data: dict) -> None:
    """
    Append a single NDJSON debug log line for debug mode.
    """
    payload = {
        "sessionId": "debug-session",
        "runId": "pre-fix",
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    try:
        from core.debug_utils import DEBUG_LOG_PATH
        import os

        os.makedirs(DEBUG_LOG_PATH.parent, exist_ok=True)
        with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        # Logging must never break the request
        pass


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
        # region agent log
        _agent_debug_log(
            hypothesis_id="H1_H3",
            location="api.v1.views.keywords.KeywordPlannerRunImportCsvView.post:before_params",
            message="Import CSV request received",
            data={
                "has_file": bool(csv_file),
                "file_name": getattr(csv_file, "name", None),
                "content_type": getattr(csv_file, "content_type", None),
                "data_keys": list(request.data.keys()),
            },
        )
        # endregion agent log
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

        # region agent log
        _agent_debug_log(
            hypothesis_id="H1_H2",
            location="api.v1.views.keywords.KeywordPlannerRunImportCsvView.post:before_import",
            message="Validated CSV import params",
            data={
                "locale_code": data.get("locale_code"),
                "channel_code": data.get("channel_code"),
                "has_run_id": bool(data.get("run_id")),
                "has_product_type_id": bool(data.get("product_type_id")),
                "delimiter": data.get("delimiter"),
            },
        )
        # endregion agent log

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
            # region agent log
            _agent_debug_log(
                hypothesis_id="H2_H3",
                location="api.v1.views.keywords.KeywordPlannerRunImportCsvView.post:exception",
                message="Unexpected error during CSV import",
                data={"error_type": type(e).__name__, "error_str": str(e)},
            )
            # endregion agent log
            import traceback

            return Response(
                {
                    "detail": str(e),
                    "error_type": type(e).__name__,
                    "traceback": traceback.format_exc(),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # region agent log
        _agent_debug_log(
            hypothesis_id="H1",
            location="api.v1.views.keywords.KeywordPlannerRunImportCsvView.post:success",
            message="CSV import completed",
            data={"run_id": result.get("run_id"), "keywords_created": result.get("keywords_created")},
        )
        # endregion agent log

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
    """GET: list attribute mappings for this run (paginated)."""

    def get(self, request, run_id: int):
        page = int(request.query_params.get("page", 1))
        page_size = min(int(request.query_params.get("page_size", 50)), 100)
        offset = (page - 1) * page_size
        qs = (
            AttributeMap.objects.filter(origin_run_keyword__run_id=run_id)
            .select_related("keyword", "attribute", "attribute_value")
            .order_by("keyword__term", "attribute__code")
        )
        total = qs.count()
        items = qs[offset : offset + page_size]
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


class KeywordPlannerRunPersistMappingsView(APIView):
    """
    POST: persist per-product keyword mappings (with optional LLM).
    GET: describe the endpoint (for DRF browsable API / discovery).
    """

    def get(self, request, run_id: int):
        return Response(
            {
                "run_id": run_id,
                "action": "persist_product_keyword_maps",
                "method": "POST",
                "description": "Persist per-product keyword mappings for this planner run. "
                "Optional body: product_id, limit, min_confidence, include_text_values, include_i18n, "
                "include_descriptions, max_description_chars, max_text_matches, max_enum_maps, "
                "use_llm, llm_max_keywords, dry_run.",
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request, run_id: int):
        # #region agent log
        def _agent_log(loc, msg, data, hid):
            import os
            import sys
            _payload = __import__("json").dumps({"location": loc, "message": msg, "data": data, "hypothesisId": hid, "timestamp": __import__("time").time() * 1000})
            try:
                sys.stdout.write("[AGENT_DEBUG] " + _payload + "\n")
                sys.stdout.flush()
            except Exception:
                pass
            _base = getattr(settings, "BASE_DIR", None)
            _root = str(_base) if _base is not None else os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            _p = os.path.join(_root, ".cursor", "debug.log")
            try:
                os.makedirs(os.path.dirname(_p), exist_ok=True)
                with open(_p, "a") as _f:
                    _f.write(_payload + "\n")
            except Exception:
                pass
        try:
            _agent_log("keywords.py:post:first_line", "view entered", {"run_id": run_id}, "H2")
        except Exception:
            pass
        try:
            _data = getattr(request, "data", None)
            _keys = list(_data.keys()) if isinstance(_data, dict) else ("no-dict",)
            _agent_log("keywords.py:post:entry", "persist view entry", {"run_id": run_id, "data_keys": _keys}, "H2")
        except Exception as _ex:
            _agent_log("keywords.py:post:entry_failed", "request.data failed", {"run_id": run_id, "exc": type(_ex).__name__, "msg": str(_ex)[:200]}, "H2")
        # #endregion
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
            llm_max_keywords = request.data.get("llm_max_keywords", 80)
            dry_run = request.data.get("dry_run", False)
            focus_on = (request.data.get("focus_on") or "").strip() or None
            ignore = (request.data.get("ignore") or "").strip() or None
            ignore_size_and_marketplace = request.data.get("ignore_size_and_marketplace", False) is True
            focus_head_terms = request.data.get("focus_head_terms", False) is True
            focus_hook_terms = request.data.get("focus_hook_terms", False) is True
            # #region agent log
            try:
                _agent_log("keywords.py:post:before_persist", "calling persist_product_keyword_maps", {"run_id": run_id}, "H1")
            except Exception:
                pass
            # #endregion
            result = persist_product_keyword_maps(
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
                llm_max_keywords=llm_max_keywords,
                dry_run=dry_run,
                focus_on=focus_on,
                ignore=ignore,
                ignore_size_and_marketplace=ignore_size_and_marketplace,
                focus_head_terms=focus_head_terms,
                focus_hook_terms=focus_hook_terms,
            )
            # #region agent log
            try:
                _agent_log("keywords.py:post:after_persist", "persist returned", dict(result) if isinstance(result, dict) else {}, "H1")
            except Exception:
                pass
            # #endregion
            return Response(result)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # #region agent log
            try:
                _agent_log("keywords.py:post:except", "exception in view", {"exc_type": type(e).__name__, "exc_msg": str(e)[:500]}, "H1,H3")
            except Exception:
                pass
            # #endregion
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
            per_product = max(1, max_hook_terms // max(len(product_ids), 1))
            all_hook = []
            for pid in product_ids[:50]:
                hook_list = extract_suggested_hook_terms(
                    run=run,
                    product_id=pid,
                    locale_id=locale_id,
                    channel_id=channel_id,
                    head_terms_normalized=head_norm,
                    max_terms=min(per_product, 20),
                )
                all_hook.extend(hook_list)
            all_hook.sort(key=lambda x: (-x["avg_searches"], x["term"]))
            suggested_hook = all_hook[:max_hook_terms]

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
