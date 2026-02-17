import logging

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
from pub.services.content_generation import generate_content, preview_content
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
    queryset = ExportJob.objects.all().order_by("-id")
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

        variant = Variant.objects.select_related("product", "product__product_type").get(id=data["variant_id"])
        locale = Locale.objects.get(code=data["locale_code"])
        channel = Channel.objects.get(code=data["channel_code"])
        planner_run = None
        if data.get("planner_run_id"):
            planner_run = PlannerRun.objects.get(id=data["planner_run_id"])

        response = preview_content(
            variant=variant,
            locale=locale,
            channel=channel,
            run=planner_run,
            context=data.get("context", "title"),
            include_descriptions=data.get("include_descriptions", False),
        )
        return Response(response, status=status.HTTP_200_OK)


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
            batch_id=data["batch_id"],
        )
        run_export_job(job=job)
        return Response(ExportJobSerializer(job).data, status=status.HTTP_201_CREATED)


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
        "planner_run_id": 456  // optional
    }
    """
    
    def post(self, request, listing_id: int):
        try:
            data = request.data or {}
            locale_code = data.get('locale_code')
            raw_template_id = data.get('template_id')
            raw_planner_run_id = data.get('planner_run_id')
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
            # #region agent log
            try:
                from core.debug_utils import DEBUG_LOG_PATH
                import json
                with open(DEBUG_LOG_PATH, "a") as f:
                    f.write(json.dumps({"message": "view before generate_titles_for_listing", "data": {"listing_id": listing_id}, "hypothesisId": "H5", "location": "pub.views"}) + "\n")
            except Exception:
                pass
            # #endregion
            result = generate_titles_for_listing(
                listing_id=listing_id,
                locale_code=str(locale_code),
                template_id=template_id,
                planner_run_id=planner_run_id,
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
            # #region agent log
            try:
                from core.debug_utils import DEBUG_LOG_PATH
                import json
                with open(DEBUG_LOG_PATH, "a") as f:
                    f.write(json.dumps({"message": "view except", "data": {"exc_type": type(exc).__name__, "exc_msg": str(exc)[:200]}, "hypothesisId": "H5", "location": "pub.views"}) + "\n")
            except Exception:
                pass
            # #endregion
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
    GET /generated-titles/?locale_code=xx&channel_code=yy&page=1&page_size=100
    Returns all generated titles in the database, optionally filtered by locale and/or channel.
    Latest per (variant, channel, locale). Paginated.
    """

    def get(self, request):
        locale_code = request.query_params.get("locale_code") or None
        channel_code = request.query_params.get("channel_code") or None
        try:
            page = int(request.query_params.get("page", 1))
            page_size = int(request.query_params.get("page_size", 100))
        except (TypeError, ValueError):
            page, page_size = 1, 100
        page_size = min(max(1, page_size), 500)
        page = max(1, page)
        result = get_all_generated_titles(
            locale_code=locale_code,
            channel_code=channel_code,
            page=page,
            page_size=page_size,
        )
        return Response(result, status=status.HTTP_200_OK)
