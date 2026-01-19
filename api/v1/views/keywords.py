from django.db.models import Max
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from api.v1.serializers import (
    KeywordSerializer,
    MetricSerializer,
    PlannerRunCreateSerializer,
    PlannerRunKeywordSerializer,
    PlannerRunSerializer,
    PlannerSeedSerializer,
)
from content.models import Locale
from kw.models import Keyword, KeywordStatus, Metric, PlannerRun, PlannerRunKeyword, PlannerSeed, Source
from kw.services.seed_builder import _normalize
from pub.models import Channel


class PlannerRunViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PlannerRun.objects.select_related("source", "locale", "product_type", "channel").order_by("-id")
    serializer_class = PlannerRunSerializer


class PlannerRunKeywordViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PlannerRunKeyword.objects.select_related("keyword", "run").order_by("-id")
    serializer_class = PlannerRunKeywordSerializer


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


class KeywordPlannerRunDetailView(APIView):
    def get(self, request, run_id: int):
        run = PlannerRun.objects.select_related("locale", "channel", "product_type").get(id=run_id)
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
            keywords_payload.append(
                {
                    "id": prk.id,
                    "keyword_id": prk.keyword_id,
                    "term": prk.keyword.term,
                    "status": prk.status,
                    "concept": prk.concept,
                    "avg_searches": metric.get("avg_searches"),
                    "competition": metric.get("competition"),
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
