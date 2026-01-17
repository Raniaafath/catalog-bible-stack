from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from api.v1.serializers import (
    ContentGenerateRequestSerializer,
    ContentPreviewRequestSerializer,
    ContentSetItemSerializer,
    ContentSetSerializer,
    ExportJobCreateSerializer,
    ExportJobSerializer,
    ExportProfileSerializer,
    GenerationBatchCreateSerializer,
    GenerationBatchItemSerializer,
    GenerationBatchSerializer,
    GenerationRunSerializer,
    TemplatePartSerializer,
    TemplateSerializer,
    TitleGenerateRequestSerializer,
    TitleSuggestionsQuerySerializer,
)
from api.v1.views.mixins import IntegrityErrorTo409Mixin
from catalog.models import Product, Variant
from content.models import Locale
from kw.models import PlannerRun
from pub.models import (
    Channel,
    ContentSet,
    ContentSetItem,
    ExportJob,
    ExportProfile,
    GenerationBatch,
    GenerationBatchItem,
    GenerationRun,
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


class TemplatePartViewSet(IntegrityErrorTo409Mixin, viewsets.ModelViewSet):
    queryset = TemplatePart.objects.select_related("template", "attribute").order_by("template_id", "position", "id")
    serializer_class = TemplatePartSerializer


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
