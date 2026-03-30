import logging
import os

from django.http import FileResponse, Http404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)

from api.v1.serializers import (
    ChannelListingCreateSerializer,
    ChannelListingDetailSerializer,
    ChannelListingSerializer,
    ContentGenerateRequestSerializer,
    ContentPreviewRequestSerializer,
    SaveContentSelectionSerializer,
    ContentSetItemSerializer,
    ContentSetSerializer,
    ChannelSerializer,
    ChannelLocalePolicySerializer,
    ChannelPolicySetSerializer,
    ExportJobCreateSerializer,
    ExportJobSerializer,
    ExportProfileSerializer,
    GenerationBatchCreateSerializer,
    GenerationBatchItemSerializer,
    GenerationBatchSerializer,
    GenerationRunSerializer,
    MoveVariantsSerializer,
    RemoveVariantsSerializer,
    SetListingAxesSerializer,
    TemplatePartSerializer,
    TemplateSerializer,
    TitleGenerateRequestSerializer,
    TitleSuggestionsQuerySerializer,
)
from api.v1.serializers.catalog import VariantAttributeDetailsSerializer
from django.db import models
from django.db.models.deletion import ProtectedError
from api.v1.views.mixins import IntegrityErrorTo409Mixin
from catalog.models import Attribute, AttributeValue, Product, ProductAttributeValue, Variant
from catalog.services import (
    ChannelListingError,
    ListingNotFoundError,
    ProductMismatchError,
    VariantNotFoundError,
    create_channel_listing,
    create_default_title_template_for_listing,
    generate_titles_for_listing,
    get_all_generated_titles,
    get_available_templates_for_listing,
    get_available_variants_for_listing,
    get_listing_differences,
    get_listing_generated_titles,
    move_variants_to_listing,
    update_listing_generated_title,
    remove_variants_from_listing,
    set_listing_axes,
)
from content.models import AttributeValueI18n, Locale, ProductAttributeValueI18n
from kw.models import PlannerRun
from pub.models import (
    Channel,
    ChannelListing,
    ChannelLocalePolicy,
    ChannelPolicySet,
    ContentSet,
    ContentSetItem,
    ExportJob,
    ExportProfile,
    GenerationBatch,
    GenerationBatchItem,
    GenerationRun,
    TitleSelection,
    Template,
    TemplatePart,
)
from pub.services.content_batches import create_batch
from pub.services.export_service import run_export_job
from pub.services.dtos import TitleGenerationRequest
from pub.services.generation_service import TitleGenerationServiceError, generate_titles
from pub.services.ai_constants import (
    DEFAULT_DESCRIPTION_AI_MODEL,
    DEFAULT_TITLE_POLISH_INSTRUCTIONS,
    OPENAI_TITLE_AI_MODELS,
)
from pub.services.content_generation import generate_content, preview_content, save_content_selection
from pub.services.title_renderer import TitleApprovalRequired, TitleRenderError, get_title_suggestions


class TemplateViewSet(IntegrityErrorTo409Mixin, viewsets.ModelViewSet):
    queryset = Template.objects.select_related("product_type", "locale", "channel").order_by("-id")
    serializer_class = TemplateSerializer

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError as e:
            count = len(e.protected_objects) if e.protected_objects else 0
            return Response(
                {
                    "detail": (
                        f"This template cannot be deleted because it is used by {count} "
                        "title generation run(s). Archive it instead (set status to 'archived') "
                        "or delete the generation runs first."
                    ),
                    "protected_count": count,
                },
                status=status.HTTP_409_CONFLICT,
            )


class TemplatePartViewSet(IntegrityErrorTo409Mixin, viewsets.ModelViewSet):
    serializer_class = TemplatePartSerializer

    def get_queryset(self):
        queryset = TemplatePart.objects.select_related("template", "attribute").order_by("template_id", "position", "id")
        template_id = self.request.query_params.get("template_id")
        if template_id:
            queryset = queryset.filter(template_id=template_id)
        return queryset


class QuickCreateTemplateView(APIView):
    """
    POST /templates/quick-create/
    Create a template in one shot using AI to select and order attributes.
    Works for any product type and any language.
    If a keyword run is provided, attribute candidates are ranked by search volume first.
    If no run is provided, falls back to all use_in_title attributes for the product type.
    """

    def post(self, request):
        import json, os
        from django.db import transaction
        from catalog.models import ProductType, ProductTypeAttribute

        product_type_id = request.data.get("product_type_id")
        channel_code = (request.data.get("channel_code") or "").strip()
        locale_code = (request.data.get("locale_code") or "").strip()
        run_id = request.data.get("run_id")
        ai_model = (request.data.get("ai_model") or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")).strip()

        if not product_type_id or not channel_code or not locale_code:
            return Response({"detail": "product_type_id, channel_code, and locale_code are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product_type = ProductType.objects.get(id=product_type_id)
        except ProductType.DoesNotExist:
            return Response({"detail": "Product type not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            channel = Channel.objects.get(code=channel_code, is_active=True)
        except Channel.DoesNotExist:
            return Response({"detail": "Channel not found or inactive."}, status=status.HTTP_404_NOT_FOUND)
        try:
            locale = Locale.objects.get(code=locale_code)
        except Locale.DoesNotExist:
            return Response({"detail": "Locale not found."}, status=status.HTTP_404_NOT_FOUND)

        # Next version number for this scope
        existing_versions = list(
            Template.objects.filter(
                product_type=product_type, channel=channel, locale=locale, kind=Template.Kind.TITLE
            ).values_list("version", flat=True)
        )
        next_version = (max(existing_versions) + 1) if existing_versions else 1

        # ── Axis attributes (variant-level → always position 2) ─────────────
        axis_attributes = []
        axis_attr_codes: set = set()
        for pta in ProductTypeAttribute.objects.filter(
            product_type=product_type, variant_level=True
        ).select_related("attribute").order_by("id"):
            axis_attributes.append({"attribute_id": pta.attribute.id, "attribute_code": pta.attribute.code})
            axis_attr_codes.add(pta.attribute.code)

        # ── Candidate attributes for positions 3+ ───────────────────────────
        proposed = []
        source = "fallback"

        if run_id:
            try:
                from kw.models import PlannerRun, ProductKeywordMap, Metric
                from django.db.models import Max, Sum, Count, OuterRef, Subquery, Value, IntegerField
                from django.db.models.functions import Coalesce
                run = PlannerRun.objects.filter(id=run_id).first()
                if run:
                    kw_vol_sq = (
                        Metric.objects.filter(keyword_id=OuterRef("keyword_id"))
                        .values("keyword_id").annotate(v=Max("avg_searches")).values("v")[:1]
                    )
                    rows = (
                        ProductKeywordMap.objects.filter(run=run, attribute__isnull=False, attribute__use_in_title=True)
                        .annotate(kw_vol=Subquery(kw_vol_sq, output_field=IntegerField()))
                        .values("attribute_id", "attribute__code", "attribute__data_type", "attribute__unit")
                        .annotate(
                            total_vol=Sum(Coalesce("kw_vol", Value(0))),
                            keyword_count=Count("keyword_id", distinct=True),
                        )
                        .order_by("-total_vol")[:10]
                    )
                    proposed = [
                        {
                            "attribute_id": r["attribute_id"],
                            "attribute_code": r["attribute__code"],
                            "data_type": r["attribute__data_type"],
                            "unit": r["attribute__unit"],
                            "total_vol": r["total_vol"] or 0,
                            "reason": None,
                        }
                        for r in rows if r["attribute__code"] not in axis_attr_codes
                    ]
                    source = "volume"
            except Exception:
                pass

        if not proposed:
            # First try product type attributes
            pta_qs = list(ProductTypeAttribute.objects.filter(
                product_type=product_type, attribute__use_in_title=True
            ).select_related("attribute").exclude(attribute__code__in=axis_attr_codes).order_by("id"))
            if pta_qs:
                for pta in pta_qs:
                    proposed.append({
                        "attribute_id": pta.attribute.id,
                        "attribute_code": pta.attribute.code,
                        "data_type": pta.attribute.data_type,
                        "unit": getattr(pta.attribute, "unit", None),
                        "total_vol": 0,
                        "reason": None,
                    })
            else:
                # No product type attributes configured — fall back to ALL use_in_title attributes
                # so it works with any product type without needing pre-configuration
                for attr in Attribute.objects.filter(use_in_title=True).exclude(code__in=axis_attr_codes).order_by("code"):
                    proposed.append({
                        "attribute_id": attr.id,
                        "attribute_code": attr.code,
                        "data_type": attr.data_type,
                        "unit": getattr(attr, "unit", None),
                        "total_vol": 0,
                        "reason": None,
                    })
            source = "fallback"

        # ── AI reorder + select ──────────────────────────────────────────────
        if proposed:
            pt_label = (product_type.default_label or product_type.code or "").strip()
            pt_category = (getattr(product_type, "main_category", "") or "").strip()
            product_context = f"{pt_label} ({pt_category})" if pt_category else pt_label
            lang_code = locale_code.split("-")[0].lower()
            lang_name = {
                "fr": "French", "de": "German", "es": "Spanish", "it": "Italian",
                "pt": "Portuguese", "nl": "Dutch", "pl": "Polish", "en": "English",
                "ja": "Japanese", "zh": "Chinese", "ko": "Korean", "ar": "Arabic",
                "sv": "Swedish", "da": "Danish", "fi": "Finnish", "no": "Norwegian",
            }.get(lang_code, locale_code)
            first_attr_pos = 3 + len(axis_attributes)  # 1=head, 2=hook, 3..N=axis attrs
            attr_lines = "\n".join(
                f"{first_attr_pos + i}. {p['attribute_code']}"
                f"{' [' + p['data_type'] + ']' if p.get('data_type') else ''}"
                f"{' (unit: ' + p['unit'] + ')' if p.get('unit') else ''}"
                + (f" — {p['total_vol']:,} searches" if p.get("total_vol") else "")
                for i, p in enumerate(proposed)
            )
            axis_label = ", ".join(a["attribute_code"] for a in axis_attributes) if axis_attributes else "none configured"
            system_prompt = (
                f"You are an e-commerce SEO expert selecting product attributes for marketplace titles in {lang_name} ({locale_code}). "
                "The title structure is fixed: [head term] → [hook] → [variation axis attributes] → [your attributes]. "
                "Select and order the most buyer-relevant descriptive attributes from the candidates below. "
                "Exclude attributes that are redundant or low-value for this product type. "
                "Broad/defining attributes go first, specific/technical ones last. "
                "Do NOT add new attributes — only pick from the provided list. "
                "Write your reasons in the target language. Return valid JSON only."
            )
            user_prompt = (
                f"Product type: {product_context}\n"
                f"Locale: {locale_code} ({lang_name})\n\n"
                f"Fixed title structure:\n"
                f"  Position 1: [head term] — product category label\n"
                f"  Position 2: [hook] — product name/model\n"
                f"  Position 3+: [{axis_label}] — variation axis, already included automatically\n\n"
                f"Candidate descriptive attributes for the remaining positions:\n{attr_lines}\n\n"
                "Select the best ones and order them. Do NOT re-select the axis attributes already listed above.\n"
                'Return JSON: {"proposed": [{"attribute_code": "...", "reason": "..."}]}'
            )
            raw = None
            try:
                if ai_model.startswith("claude-"):
                    api_key = os.environ.get("ANTHROPIC_API_KEY")
                    if api_key:
                        import anthropic
                        client = anthropic.Anthropic(api_key=api_key)
                        msg = client.messages.create(
                            model=ai_model, max_tokens=900, system=system_prompt,
                            messages=[{"role": "user", "content": user_prompt}], temperature=0,
                        )
                        raw = msg.content[0].text if msg.content else None
                elif ai_model.startswith("gemini-"):
                    api_key = os.environ.get("GOOGLE_AI_API_KEY")
                    if api_key:
                        import google.generativeai as genai
                        genai.configure(api_key=api_key)
                        g = genai.GenerativeModel(
                            model_name=ai_model, system_instruction=system_prompt,
                            generation_config={"temperature": 0, "max_output_tokens": 900, "response_mime_type": "application/json"},
                        )
                        raw = g.generate_content(user_prompt).text
                else:
                    api_key = os.environ.get("OPENAI_API_KEY")
                    if api_key:
                        from openai import OpenAI
                        client = OpenAI(api_key=api_key)
                        resp = client.chat.completions.create(
                            model=ai_model, temperature=0, max_tokens=900,
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
                    cleaned = raw.strip()
                    if cleaned.startswith("```"):
                        lines = cleaned.split("\n")
                        cleaned = "\n".join(lines[1:]).rsplit("```", 1)[0]
                    ai_result = json.loads(cleaned)
                    ai_codes = [x["attribute_code"] for x in ai_result.get("proposed", []) if x.get("attribute_code")]
                    reasons = {x["attribute_code"]: x.get("reason") for x in ai_result.get("proposed", [])}
                    code_to_attr = {p["attribute_code"]: p for p in proposed}
                    reordered = []
                    for code in ai_codes:
                        if code in code_to_attr:
                            a = dict(code_to_attr[code])
                            a["reason"] = reasons.get(code)
                            reordered.append(a)
                    if reordered:
                        proposed = reordered
                        source = "ai"
                except Exception:
                    pass

        # ── Create template + parts atomically ──────────────────────────────
        with transaction.atomic():
            template = Template.objects.create(
                product_type=product_type, locale=locale, channel=channel,
                kind=Template.Kind.TITLE, version=next_version, status=Template.Status.DRAFT,
            )
            pos = 0
            # Position 1: head term (always)
            TemplatePart.objects.create(template=template, position=pos, part_type=TemplatePart.PartType.HEAD_TERM)
            pos += 1
            # Position 2: hook term (always)
            TemplatePart.objects.create(template=template, position=pos, part_type=TemplatePart.PartType.HOOK_TERM)
            pos += 1
            # Position 3+: for each variant-level axis, create AXIS_ATTRIBUTE + ATTRIBUTE_VALUE pair.
            # Renderer skips the ATTRIBUTE_VALUE if AXIS_ATTRIBUTE already rendered it (dedup at line 413).
            # If the product doesn't use that attribute as axis, ATTRIBUTE_VALUE renders it as fallback.
            axis_attr_objs = {a["attribute_code"]: Attribute.objects.filter(id=a["attribute_id"]).first() for a in axis_attributes}
            for a in axis_attributes:
                attr_obj = axis_attr_objs.get(a["attribute_code"])
                if attr_obj:
                    TemplatePart.objects.create(template=template, position=pos, part_type=TemplatePart.PartType.AXIS_ATTRIBUTE, attribute=attr_obj)
                    pos += 1
                    TemplatePart.objects.create(template=template, position=pos, part_type=TemplatePart.PartType.ATTRIBUTE_VALUE, attribute=attr_obj)
                    pos += 1
            # Then: AI-picked attribute values (already deduped against axis_attr_codes)
            for p in proposed:
                attr_obj = Attribute.objects.filter(id=p["attribute_id"]).first()
                if attr_obj:
                    TemplatePart.objects.create(template=template, position=pos, part_type=TemplatePart.PartType.ATTRIBUTE_VALUE, attribute=attr_obj)
                    pos += 1

        structure = ["Head term", "Hook term"]
        structure += [f"Axis: {a['attribute_code']}" for a in axis_attributes]
        structure += [p["attribute_code"] for p in proposed]

        return Response({
            "template_id": template.id,
            "source": source,
            "structure": structure,
            "attributes": [{"attribute_code": p["attribute_code"], "reason": p.get("reason")} for p in proposed],
            "axis_attributes": axis_attributes,
        }, status=status.HTTP_201_CREATED)


class GenerationRunViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GenerationRun.objects.select_related(
        "product",
        "variant",
        "locale",
        "channel",
        "template",
    ).prefetch_related("outputs")
    serializer_class = GenerationRunSerializer


class ContentSetViewSet(IntegrityErrorTo409Mixin, viewsets.ModelViewSet):
    queryset = ContentSet.objects.all().order_by("-id")
    serializer_class = ContentSetSerializer


class GenerationBatchViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GenerationBatch.objects.all().order_by("-id")
    serializer_class = GenerationBatchSerializer


class ExportProfileViewSet(IntegrityErrorTo409Mixin, viewsets.ModelViewSet):
    queryset = ExportProfile.objects.all().order_by("-id")
    serializer_class = ExportProfileSerializer


class ExportJobViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ExportJob.objects.select_related("profile").order_by("-id")
    serializer_class = ExportJobSerializer


class ChannelViewSet(viewsets.ModelViewSet):
    queryset = Channel.objects.all().order_by("code")
    serializer_class = ChannelSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """Allow filtering by is_active if needed"""
        queryset = super().get_queryset()
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")
        return queryset


class ChannelPolicySetViewSet(viewsets.ModelViewSet):
    queryset = ChannelPolicySet.objects.select_related("channel").order_by("-id")
    serializer_class = ChannelPolicySetSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """Allow filtering by channel and status"""
        queryset = super().get_queryset()
        channel_id = self.request.query_params.get("channel_id")
        status_filter = self.request.query_params.get("status")
        
        if channel_id:
            queryset = queryset.filter(channel_id=channel_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset


class ChannelLocalePolicyViewSet(viewsets.ModelViewSet):
    queryset = ChannelLocalePolicy.objects.select_related(
        "policy_set__channel", "locale"
    ).order_by("-id")
    serializer_class = ChannelLocalePolicySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """Allow filtering by channel, locale, and policy_set"""
        queryset = super().get_queryset()
        channel_id = self.request.query_params.get("channel_id")
        locale_id = self.request.query_params.get("locale_id")
        policy_set_id = self.request.query_params.get("policy_set_id")
        
        if channel_id:
            queryset = queryset.filter(policy_set__channel_id=channel_id)
        if locale_id:
            queryset = queryset.filter(locale_id=locale_id)
        if policy_set_id:
            queryset = queryset.filter(policy_set_id=policy_set_id)
        
        return queryset


class TitleGenerateView(APIView):
    def post(self, request):
        serializer = TitleGenerateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request_dto = TitleGenerationRequest(
            variant_ids=serializer.validated_data["variant_ids"],
            locale_code=serializer.validated_data["locale_code"],
            channel_code=serializer.validated_data["channel_code"],
            planner_run_id=serializer.validated_data.get("planner_run_id"),
            include_descriptions=serializer.validated_data.get("include_descriptions", False),
            title_mode_override=serializer.validated_data.get("title_mode_override"),
            context=serializer.validated_data.get("context", "title"),
            improve_title=serializer.validated_data.get("improve_title", False),
            title_ai_model=serializer.validated_data.get("title_ai_model", ""),
            title_ai_instructions=serializer.validated_data.get("title_ai_instructions", ""),
        )
        try:
            result = generate_titles(request_dto)
        except (TitleGenerationServiceError, TitleRenderError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        outputs = [
            {
                "status": item.status,
                "variant_id": item.variant_id,
                "product_id": item.product_id,
                "output_id": item.output_id,
                "run_id": item.run_id,
                "template_id": item.template_id,
                "title": item.title,
                "selection_id": item.selection_id,
                "preview_title": item.preview_title,
                "suggestions": item.suggestions,
            }
            for item in result.outputs
        ]
        response = {
            "status": "completed",
            "outputs": outputs,
        }
        return Response(response, status=status.HTTP_202_ACCEPTED)


class ContentPreviewView(APIView):
    def post(self, request):
        serializer = ContentPreviewRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            variant = Variant.objects.select_related("product", "product__product_type").get(id=data["variant_id"])
            locale = Locale.objects.get(code=data["locale_code"])
            channel = Channel.objects.get(code=data["channel_code"])
        except (Variant.DoesNotExist, Locale.DoesNotExist, Channel.DoesNotExist) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        planner_run = None
        if data.get("planner_run_id"):
            try:
                planner_run = PlannerRun.objects.get(id=data["planner_run_id"])
            except PlannerRun.DoesNotExist:
                return Response({"detail": "planner_run_id not found."}, status=status.HTTP_404_NOT_FOUND)

        instructions = (data.get("description_instructions") or "").strip()
        improve_description = bool(data.get("include_descriptions") and instructions)
        response = preview_content(
            variant=variant,
            locale=locale,
            channel=channel,
            run=planner_run,
            context=data.get("context", "title"),
            include_descriptions=data.get("include_descriptions", False),
            improve_description=improve_description,
            description_user_instructions=instructions,
            description_ai_model=(data.get("description_model") or DEFAULT_DESCRIPTION_AI_MODEL).strip() or DEFAULT_DESCRIPTION_AI_MODEL,
        )
        return Response(response, status=status.HTTP_200_OK)


class ContentSaveSelectionView(APIView):
    """
    Save current preview (description + bullets) as a draft content selection.
    POST /content/save-selection/
    """

    def post(self, request):
        serializer = SaveContentSelectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        selection = save_content_selection(
            variant_id=data["variant_id"],
            locale_code=data["locale_code"],
            channel_code=data["channel_code"],
            description=data["description"],
            bullets=data.get("bullets") or [],
            context=data.get("context", "title"),
        )
        return Response(
            {"id": selection.id, "status": selection.status, "detail": "Content saved as draft."},
            status=status.HTTP_200_OK,
        )


class VariantAttributeDetailsView(APIView):
    """
    Return attribute values for a variant, including translated values for a given locale.

    GET /variants/{variant_id}/attribute-details/?locale_code=de-DE&channel_code=shopify
    """

    def get(self, request, variant_id: int):
        locale_code = request.query_params.get("locale_code")
        if not locale_code:
            return Response(
                {"detail": "locale_code query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            variant = Variant.objects.select_related("product", "product__product_type").get(id=variant_id)
        except Variant.DoesNotExist:
            return Response(
                {"detail": f"Variant {variant_id} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            locale = Locale.objects.get(code=locale_code)
        except Locale.DoesNotExist:
            return Response(
                {"detail": f"Locale {locale_code} not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Collect product- and variant-level PAVs, preferring variant-level when both exist
        pav_qs = (
            ProductAttributeValue.objects.filter(
                models.Q(variant=variant) | models.Q(product=variant.product)
            )
            .select_related("attribute", "attribute_value", "attribute_value__attribute")
            .order_by("attribute__code", "id")
        )
        pav_by_attr: dict[int, ProductAttributeValue] = {}
        for pav in pav_qs:
            key = pav.attribute_id
            existing = pav_by_attr.get(key)
            # Prefer variant-level over product-level
            if existing is None or (existing.variant_id is None and pav.variant_id is not None):
                pav_by_attr[key] = pav

        pavs = list(pav_by_attr.values())

        # Load enum translations and per-PAV translations
        attr_value_ids = [pav.attribute_value_id for pav in pavs if pav.attribute_value_id]
        pav_ids = [pav.id for pav in pavs]

        attr_i18n: dict[int, str] = {}
        if attr_value_ids:
            for row in AttributeValueI18n.objects.filter(
                attribute_value_id__in=attr_value_ids, locale=locale
            ).values("attribute_value_id", "label"):
                attr_i18n[row["attribute_value_id"]] = row["label"]

        pav_i18n: dict[int, str] = {}
        if pav_ids:
            for row in ProductAttributeValueI18n.objects.filter(
                product_attribute_value_id__in=pav_ids, locale=locale
            ).values("product_attribute_value_id", "value_text"):
                if row["value_text"]:
                    pav_i18n[row["product_attribute_value_id"]] = row["value_text"]

        # Build response items
        items = []
        for pav in pavs:
            attr: Attribute = pav.attribute
            data_type = attr.data_type
            # Attribute is variant-level if there is a ProductTypeAttribute row
            # for this product type with variant_level=True.
            is_variant_level = attr.product_types.filter(
                product_type=variant.product.product_type,
                variant_level=True,
            ).exists()

            raw_value = None
            translated_value = None
            source = "raw"

            if data_type == Attribute.DataType.ENUM and pav.attribute_value_id:
                av: AttributeValue | None = pav.attribute_value
                raw_value = av.code if av else None
                # Prefer per-PAV translation, then shared enum translation
                if pav.id in pav_i18n:
                    translated_value = pav_i18n[pav.id]
                    source = "enum_pav_i18n"
                elif pav.attribute_value_id in attr_i18n:
                    translated_value = attr_i18n[pav.attribute_value_id]
                    source = "enum_i18n"
                else:
                    source = "enum_code"
            else:
                # Non-enum: use PAV translations if present, else raw value fields
                if pav.id in pav_i18n:
                    translated_value = pav_i18n[pav.id]
                    source = "pav_i18n"
                # Determine raw value from underlying fields
                if pav.value_text not in (None, ""):
                    raw_value = pav.value_text
                elif pav.attribute_value_id:
                    # text attrs stored as AttributeValue FK by importer
                    av = pav.attribute_value
                    raw_value = av.code if av else None
                elif pav.value_number is not None:
                    raw_value = str(pav.value_number)
                elif pav.value_bool is not None:
                    raw_value = "true" if pav.value_bool else "false"
                elif pav.value_json not in (None, ""):
                    raw_value = str(pav.value_json)

            items.append(
                {
                    "attribute_id": attr.id,
                    "attribute_code": attr.code,
                    "attribute_label": attr.code,  # could be enhanced with AttributeI18n
                    "data_type": data_type,
                    "is_variant_level": is_variant_level,
                    "product_attribute_value_id": pav.id,
                    "raw_value": raw_value,
                    "translated_value": translated_value,
                    "source": source,
                }
            )

        serializer = VariantAttributeDetailsSerializer(items, many=True)
        return Response({"attributes": serializer.data})


class ContentGenerateView(APIView):
    def post(self, request):
        serializer = ContentGenerateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        locale = Locale.objects.get(code=data["locale_code"])
        channel = Channel.objects.get(code=data["channel_code"])
        planner_run = None
        if data.get("planner_run_id"):
            planner_run = PlannerRun.objects.get(id=data["planner_run_id"])

        results = []
        variants = Variant.objects.select_related("product", "product__product_type").filter(id__in=data["variant_ids"])
        for variant in variants:
            try:
                result = generate_content(
                    variant=variant,
                    locale=locale,
                    channel=channel,
                    run=planner_run,
                    context=data.get("context", "title"),
                    include_descriptions=data.get("include_descriptions", False),
                    mode_override=data.get("title_mode_override"),
                )
                results.append(
                    {
                        "status": result["status"],
                        "variant_id": variant.id,
                        "product_id": variant.product_id,
                        "generation_run_id": result["generation_run_id"],
                        "outputs": result["outputs"],
                    }
                )
            except TitleApprovalRequired as exc:
                results.append(
                    {
                        "status": "needs_approval",
                        "variant_id": variant.id,
                        "product_id": variant.product_id,
                        "selection_id": exc.selection_id,
                        "preview_title": exc.preview_title,
                    }
                )
            except Exception as exc:
                logger.exception("ContentGenerateView: error for variant %s: %s", variant.id, exc)
                results.append(
                    {
                        "status": "error",
                        "variant_id": variant.id,
                        "product_id": variant.product_id,
                        "detail": str(exc),
                    }
                )
        return Response({"results": results}, status=status.HTTP_202_ACCEPTED)


class ContentSetItemView(APIView):
    def post(self, request, set_id: int):
        serializer = ContentSetItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        content_set = ContentSet.objects.get(id=set_id)
        item = ContentSetItem.objects.create(
            content_set=content_set,
            product_id=serializer.validated_data["product_id"],
            variant_id=serializer.validated_data.get("variant_id"),
        )
        return Response(ContentSetItemSerializer(item).data, status=status.HTTP_201_CREATED)

    def delete(self, request, set_id: int, item_id: int):
        ContentSetItem.objects.filter(id=item_id, content_set_id=set_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class GenerationBatchCreateView(APIView):
    def post(self, request):
        serializer = GenerationBatchCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        content_set = None
        if data.get("content_set_id"):
            content_set = ContentSet.objects.get(id=data["content_set_id"])

        locale = Locale.objects.get(code=data["locale_code"])
        channel = Channel.objects.get(code=data["channel_code"])
        planner_run = None
        if data.get("planner_run_id"):
            planner_run = PlannerRun.objects.get(id=data["planner_run_id"])

        batch = create_batch(
            content_set=content_set,
            variant_ids=data.get("variant_ids"),
            product_ids=data.get("product_ids"),
            channel=channel,
            locale=locale,
            context=data.get("context", "content"),
            planner_run=planner_run,
            mode=data.get("mode", "auto"),
            include_descriptions=data.get("include_descriptions", False),
        )
        return Response(GenerationBatchSerializer(batch).data, status=status.HTTP_201_CREATED)


class GenerationBatchItemView(APIView):
    def get(self, request, batch_id: int):
        items = GenerationBatchItem.objects.filter(batch_id=batch_id).order_by("id")
        serializer = GenerationBatchItemSerializer(items, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ExportJobCreateView(APIView):
    def post(self, request):
        serializer = ExportJobCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        job = ExportJob.objects.create(
            profile_id=data["profile_id"],
            batch_id=data.get("batch_id"),
        )
        run_export_job(job=job)
        return Response(ExportJobSerializer(job, context={"request": request}).data, status=status.HTTP_201_CREATED)


class ExportJobDownloadView(APIView):
    def get(self, request, job_id):
        try:
            job = ExportJob.objects.get(id=job_id)
        except ExportJob.DoesNotExist:
            raise Http404

        if job.status != ExportJob.Status.DONE or not job.result_file:
            return Response({"error": "File not available."}, status=status.HTTP_404_NOT_FOUND)

        if not os.path.exists(job.result_file):
            return Response({"error": "File not found on disk."}, status=status.HTTP_404_NOT_FOUND)

        ext = job.result_file.rsplit(".", 1)[-1].lower() if "." in job.result_file else "csv"
        if ext == "xlsx":
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            content_type = "text/csv"
        filename = os.path.basename(job.result_file)
        response = FileResponse(open(job.result_file, "rb"), content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class TitleSuggestionsView(APIView):
    def get(self, request):
        serializer = TitleSuggestionsQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        variant = None
        product = None
        if data.get("variant_id"):
            variant = Variant.objects.select_related("product", "product__product_type").get(id=data["variant_id"])
            product = variant.product
        elif data.get("product_id"):
            product = Product.objects.select_related("product_type").get(id=data["product_id"])

        planner_run = None
        if data.get("planner_run_id"):
            planner_run = PlannerRun.objects.get(id=data["planner_run_id"])

        locale = Locale.objects.get(code=data["locale_code"])
        channel = Channel.objects.get(code=data["channel_code"])

        suggestions = get_title_suggestions(
            variant=variant,
            product=product,
            locale=locale,
            channel=channel,
            run=planner_run,
            context=data.get("context", "title"),
            limit_head=data.get("limit_head"),
            limit_hook=data.get("limit_hook"),
            include_explanations=data.get("include_explanations", False),
        )
        return Response(suggestions, status=status.HTTP_200_OK)


# ============================================================================
# Channel Listing (Group) Views
# ============================================================================


class ChannelListingViewSet(IntegrityErrorTo409Mixin, viewsets.ModelViewSet):
    """
    ViewSet for Channel Listings (marketplace listing groups).
    
    A ChannelListing represents a listing group on a specific marketplace.
    One product can have multiple listings per channel (e.g., different
    color groupings on eBay).
    """
    queryset = ChannelListing.objects.select_related(
        "product", "channel", "locale"
    ).order_by("-id")
    
    def get_serializer_class(self):
        if self.action == "create":
            return ChannelListingCreateSerializer
        if self.action == "retrieve":
            return ChannelListingDetailSerializer
        return ChannelListingSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by product
        product_id = self.request.query_params.get("product_id")
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        
        # Filter by channel
        channel_id = self.request.query_params.get("channel_id")
        if channel_id:
            queryset = queryset.filter(channel_id=channel_id)
        
        # Filter by channel code
        channel_code = self.request.query_params.get("channel_code")
        if channel_code:
            queryset = queryset.filter(channel__code=channel_code)
        
        return queryset

    def create(self, request):
        """Create a new ChannelListing."""
        serializer = ChannelListingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        try:
            listing = create_channel_listing(
                product_id=data.get("product_id"),
                channel_id=data["channel_id"],
                locale_id=data.get("locale_id"),
                name=data.get("name", ""),
                is_default=data.get("is_default", True),
            )
            
            response_data = ChannelListingSerializer(listing).data
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except ChannelListingError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class ChannelListingMoveVariantsView(APIView):
    """
    Move variants to a channel listing (atomic operation).
    
    POST /channel-listings/{id}/move-variants/
    
    This removes variants from any other listing on the same channel
    and adds them to the specified listing. Enforces Option A:
    one variant = one listing per channel.
    """
    
    def post(self, request, listing_id: int):
        serializer = MoveVariantsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            result = move_variants_to_listing(
                listing_id=listing_id,
                variant_ids=serializer.validated_data["variant_ids"],
            )
        except ListingNotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except VariantNotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except ProductMismatchError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except ChannelListingError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(result, status=status.HTTP_200_OK)


class ChannelListingRemoveVariantsView(APIView):
    """
    Remove variants from a channel listing.
    
    POST /channel-listings/{id}/remove-variants/
    
    This removes the channel mapping entirely. The variant will
    no longer be listed on this channel.
    """
    
    def post(self, request, listing_id: int):
        serializer = RemoveVariantsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            result = remove_variants_from_listing(
                listing_id=listing_id,
                variant_ids=serializer.validated_data["variant_ids"],
            )
        except ListingNotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except ChannelListingError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(result, status=status.HTTP_200_OK)


class ChannelListingAvailableVariantsView(APIView):
    """
    Get variants that can be added to this listing (same product, not in listing),
    with variant-level attribute values for display and search.

    GET /channel-listings/{id}/available-variants/
    """
    def get(self, request, listing_id: int):
        try:
            result = get_available_variants_for_listing(listing_id=listing_id)
        except ListingNotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except ChannelListingError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class ChannelListingDifferencesView(APIView):
    """
    Get attribute differences for variants in a listing.
    
    GET /channel-listings/{id}/differences/
    
    Returns which attributes differ across variants and suggests
    good candidates for variation axes.
    """
    
    def get(self, request, listing_id: int):
        try:
            result = get_listing_differences(listing_id=listing_id)
        except ListingNotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except ChannelListingError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(result, status=status.HTTP_200_OK)


class ChannelListingAxesView(APIView):
    """
    Set variation axes for a channel listing.
    
    PUT /channel-listings/{id}/axes/
    
    Replaces all axes for the listing with the provided list.
    """
    
    def get(self, request, listing_id: int):
        try:
            listing = ChannelListing.objects.get(id=listing_id)
        except ChannelListing.DoesNotExist:
            return Response(
                {"detail": f"Listing with ID {listing_id} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        from catalog.models import ChannelListingAxis
        axes = ChannelListingAxis.objects.filter(
            listing=listing
        ).select_related("attribute").order_by("position")
        
        axes_data = [
            {
                "id": axis.id,
                "attribute_id": axis.attribute.id,
                "attribute_code": axis.attribute.code,
                "position": axis.position,
                "label_override": axis.label_override,
                "enabled": axis.enabled,
            }
            for axis in axes
        ]
        
        return Response({"listing_id": listing_id, "axes": axes_data}, status=status.HTTP_200_OK)
    
    def put(self, request, listing_id: int):
        serializer = SetListingAxesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            result = set_listing_axes(
                listing_id=listing_id,
                axes=serializer.validated_data["axes"],
            )
        except ListingNotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except ChannelListingError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(result, status=status.HTTP_200_OK)


class ChannelListingAvailableTemplatesView(APIView):
    """
    Get available templates for a channel listing.
    
    GET /channel-listings/{id}/available-templates/?locale=en
    
    Returns active templates that match the listing's product type and channel.
    """
    
    def get(self, request, listing_id: int):
        locale_code = request.query_params.get('locale')
        if not locale_code:
            return Response(
                {"detail": "locale query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        try:
            templates = get_available_templates_for_listing(listing_id, locale_code)
        except ListingNotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except ChannelListingError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({"templates": templates}, status=status.HTTP_200_OK)


class ChannelListingCreateDefaultTemplateView(APIView):
    """
    Create a default title template for a channel listing and locale.
    Default structure: [Head term] - [Hook term]. Uses saved head/hook terms.
    If an active template already exists, returns it.

    POST /channel-listings/{id}/create-default-template/
    Body: { "locale_code": "de" }
    """
    def post(self, request, listing_id: int):
        locale_code = request.data.get("locale_code")
        if not locale_code:
            return Response(
                {"detail": "locale_code is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            result = create_default_title_template_for_listing(
                listing_id=listing_id,
                locale_code=locale_code,
            )
        except ListingNotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except ChannelListingError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_201_CREATED)


class ChannelListingGenerateTitlesView(APIView):
    """
    Generate titles for all variants in a channel listing.
    
    POST /channel-listings/{id}/generate-titles/
    
    Request body:
    {
        "locale_code": "en",
        "template_id": 123,  // optional
        "planner_run_id": 456,  // optional
        "improve_title": true,  // optional
        "title_ai_model": "gpt-4o",  // optional
        "title_ai_instructions": "..."  // optional
    }
    """
    
    def post(self, request, listing_id: int):
        try:
            data = request.data or {}
            locale_code = data.get('locale_code')
            raw_template_id = data.get('template_id')
            raw_planner_run_id = data.get('planner_run_id')
            improve_title = bool(data.get('improve_title', False))
            title_ai_model = (data.get('title_ai_model') or '').strip()
            title_ai_instructions = (data.get('title_ai_instructions') or '').strip()
            template_id = None
            planner_run_id = None
            if raw_template_id is not None:
                try:
                    template_id = int(raw_template_id)
                except (TypeError, ValueError):
                    return Response(
                        {"detail": "template_id must be an integer."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            if raw_planner_run_id is not None:
                try:
                    planner_run_id = int(raw_planner_run_id)
                except (TypeError, ValueError):
                    return Response(
                        {"detail": "planner_run_id must be an integer."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
        except Exception as exc:
            logger.exception("channel-listings generate-titles request.data: %s", exc)
            return Response(
                {"detail": "Invalid request body or JSON."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not locale_code:
            return Response(
                {"detail": "locale_code is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = generate_titles_for_listing(
                listing_id=listing_id,
                locale_code=str(locale_code),
                template_id=template_id,
                planner_run_id=planner_run_id,
                improve_title=improve_title,
                title_ai_model=title_ai_model,
                title_ai_instructions=title_ai_instructions,
            )
        except ListingNotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except ChannelListingError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except (TitleGenerationServiceError, TitleRenderError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except (Locale.DoesNotExist, Channel.DoesNotExist) as exc:
            return Response(
                {"detail": f"Invalid locale_code or channel: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.exception("channel-listings generate-titles: %s", exc)
            return Response(
                {"detail": str(exc) or "Title generation failed. Check server logs."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            return Response(result, status=status.HTTP_202_ACCEPTED)
        except Exception as exc:
            logger.exception("channel-listings generate-titles response: %s", exc)
            return Response(
                {"detail": f"Failed to build response: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ChannelListingGeneratedTitlesView(APIView):
    """
    GET /channel-listings/{id}/generated-titles/?locale_code=xx
    Returns the latest generated title per variant for this listing and locale.
    """

    def get(self, request, listing_id: int):
        locale_code = request.query_params.get("locale_code")
        if not locale_code:
            return Response(
                {"detail": "locale_code query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            items = get_listing_generated_titles(listing_id=listing_id, locale_code=locale_code)
        except ListingNotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        return Response({"results": items}, status=status.HTTP_200_OK)


class ChannelListingGeneratedTitleUpdateView(APIView):
    """
    PATCH /channel-listings/{id}/generated-titles/{variant_id}/
    Body: { "locale_code": "de-DE", "title": "New title text" }
    Updates the latest generated title for this variant in the listing (channel + locale).
    """

    def patch(self, request, listing_id: int, variant_id: int):
        data = request.data or {}
        locale_code = data.get("locale_code")
        title = data.get("title")
        if not locale_code:
            return Response(
                {"detail": "locale_code is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if title is None:
            return Response(
                {"detail": "title is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            item = update_listing_generated_title(
                listing_id=listing_id,
                variant_id=variant_id,
                locale_code=str(locale_code),
                title=str(title),
            )
        except ListingNotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except ChannelListingError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(item, status=status.HTTP_200_OK)


class ProductHeadSelectionView(APIView):
    """
    Set or clear the approved head term (TitleSelection) for a product / locale / channel.

    - POST /products/{product_id}/head-selection/
      Body: { "locale_code": "de-DE", "channel_code": "shopify", "head_text": "duschtasse", "head_keyword_id"?: int }
      If head_text is null/empty, the selection is cleared (auto mode).

    - GET /products/{product_id}/head-selection/?locale_code=de-DE&channel_code=shopify
      Returns the current approved selection for this product / locale / channel (product scope), or id=null if none.
    """

    def _resolve_scope(self, product_id: int, locale_code: str, channel_code: str):
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return None, Response({"detail": "Product not found"}, status=status.HTTP_404_NOT_FOUND)
        try:
            locale = Locale.objects.get(code=locale_code)
        except Locale.DoesNotExist:
            return None, Response({"detail": f"Locale {locale_code} not found"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            channel = Channel.objects.get(code=channel_code)
        except Channel.DoesNotExist:
            return None, Response({"detail": f"Channel {channel_code} not found"}, status=status.HTTP_400_BAD_REQUEST)
        return (product, locale, channel), None

    def get(self, request, product_id: int):
        locale_code = request.query_params.get("locale_code")
        channel_code = request.query_params.get("channel_code")
        if not locale_code or not channel_code:
            return Response(
                {"detail": "locale_code and channel_code query parameters are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        scope, error_response = self._resolve_scope(product_id, locale_code, channel_code)
        if error_response is not None:
            return error_response
        product, locale, channel = scope
        selection = (
            TitleSelection.objects.filter(
                product=product,
                variant__isnull=True,
                locale=locale,
                channel=channel,
                context="title",
                status=TitleSelection.Status.APPROVED,
            )
            .order_by("-updated_at", "-id")
            .first()
        )
        if not selection:
            return Response(
                {"id": None, "head_text": None, "head_source": None, "status": None, "head_keyword_id": None},
                status=status.HTTP_200_OK,
            )
        return Response(
            {
                "id": selection.id,
                "head_text": selection.head_text,
                "head_source": selection.head_source,
                "status": selection.status,
                "head_keyword_id": selection.head_keyword_id,
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request, product_id: int):
        data = request.data or {}
        locale_code = data.get("locale_code")
        channel_code = data.get("channel_code")
        head_text = data.get("head_text")
        if not locale_code or not channel_code:
            return Response(
                {"detail": "locale_code and channel_code are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        scope, error_response = self._resolve_scope(product_id, locale_code, channel_code)
        if error_response is not None:
            return error_response
        product, locale, channel = scope

        # Clear selection (auto mode)
        if head_text in (None, "", []):
            TitleSelection.objects.filter(
                product=product,
                variant__isnull=True,
                locale=locale,
                channel=channel,
                context="title",
            ).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        selection, _created = TitleSelection.objects.update_or_create(
            product=product,
            variant=None,
            locale=locale,
            channel=channel,
            context="title",
            defaults={
                "head_text": str(head_text),
                "head_source": "manual",
                "head_keyword_id": None,
                "status": TitleSelection.Status.APPROVED,
                "created_by_type": TitleSelection.CreatedByType.USER,
            },
        )
        return Response(
            {
                "id": selection.id,
                "head_text": selection.head_text,
                "head_source": selection.head_source,
                "status": selection.status,
                "head_keyword_id": selection.head_keyword_id,
            },
            status=status.HTTP_200_OK,
        )


class AllGeneratedTitlesView(APIView):
    """
    GET    /generated-titles/                       — list (paginated, filterable)
    PATCH  /generated-titles/?run_id=X              — edit title text
    DELETE /generated-titles/?run_id=X              — delete generation run + outputs
    """

    def get(self, request):
        action = (request.query_params.get("action") or "").strip().lower()
        if action == "ai-options":
            available_models = sorted(OPENAI_TITLE_AI_MODELS)
            env_default = (os.environ.get("TITLE_AI_MODEL_DEFAULT") or os.environ.get("OPENAI_MODEL") or "").strip()
            default_model = env_default if env_default in OPENAI_TITLE_AI_MODELS else (
                "gpt-4o" if "gpt-4o" in OPENAI_TITLE_AI_MODELS else DEFAULT_DESCRIPTION_AI_MODEL
            )
            if default_model not in OPENAI_TITLE_AI_MODELS and available_models:
                default_model = available_models[0]
            default_instructions = (
                os.environ.get("TITLE_AI_INSTRUCTIONS_DEFAULT") or DEFAULT_TITLE_POLISH_INSTRUCTIONS
            ).strip()
            return Response(
                {
                    "title_ai_models": available_models,
                    "default_title_ai_model": default_model,
                    "default_title_ai_instructions": default_instructions,
                },
                status=status.HTTP_200_OK,
            )

        locale_code = request.query_params.get("locale_code") or None
        channel_code = request.query_params.get("channel_code") or None
        try:
            page = int(request.query_params.get("page", 1))
            page_size = int(request.query_params.get("page_size", 100))
        except (TypeError, ValueError):
            page, page_size = 1, 100
        page_size = min(max(1, page_size), 500)
        page = max(1, page)
        include_descriptions = request.query_params.get("include_descriptions", "").lower() in ("1", "true", "yes")
        result = get_all_generated_titles(
            locale_code=locale_code,
            channel_code=channel_code,
            page=page,
            page_size=page_size,
            include_descriptions=include_descriptions,
        )
        return Response(result, status=status.HTTP_200_OK)

    def patch(self, request):
        run_id = request.query_params.get("run_id")
        title = request.data.get("title")
        if not run_id:
            return Response({"detail": "run_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        if title is None:
            return Response({"detail": "title is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            run = GenerationRun.objects.get(id=run_id)
        except GenerationRun.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        from pub.models import GenerationOutput
        output = run.outputs.filter(field="title").first() or run.outputs.first()
        if output:
            output.text = str(title)
            output.save(update_fields=["text"])
        else:
            GenerationOutput.objects.create(run=run, field="title", text=str(title))
        return Response({"run_id": run.id, "title": str(title)}, status=status.HTTP_200_OK)

    def delete(self, request):
        run_id = request.query_params.get("run_id")
        if not run_id:
            return Response({"detail": "run_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            run = GenerationRun.objects.get(id=run_id)
        except GenerationRun.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        run.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def post(self, request):
        """
        POST /generated-titles/?action=polish
        Body: { run_id, ai_model?, instructions? }
        Returns { original, polished, explanation }
        """
        action = request.query_params.get("action")
        if action != "polish":
            return Response({"detail": "Unknown action."}, status=status.HTTP_400_BAD_REQUEST)

        run_id = request.data.get("run_id")
        ai_model = (request.data.get("ai_model") or DEFAULT_DESCRIPTION_AI_MODEL).strip()
        instructions = (request.data.get("instructions") or "").strip()

        if ai_model and ai_model not in OPENAI_TITLE_AI_MODELS:
            return Response(
                {"detail": f"Unsupported model '{ai_model}'. Allowed: {', '.join(sorted(OPENAI_TITLE_AI_MODELS))}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not run_id:
            return Response({"detail": "run_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            run = GenerationRun.objects.get(id=run_id)
        except GenerationRun.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        output = run.outputs.filter(field="title").first() or run.outputs.first()
        original = output.text if output else ""
        locale_code = run.locale.code if run.locale else "fr-FR"

        from pub.services.content_generation import polish_title_with_explanation
        result = polish_title_with_explanation(
            raw_title=original,
            locale_code=locale_code,
            user_instructions=instructions,
            model=ai_model or DEFAULT_DESCRIPTION_AI_MODEL,
        )
        return Response({"original": original, **result}, status=status.HTTP_200_OK)
