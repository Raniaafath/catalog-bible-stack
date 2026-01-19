from rest_framework import serializers

from catalog.models import ProductType
from content.models import Locale
from kw.models import Keyword, Metric, PlannerRun, PlannerRunKeyword, PlannerSeed, Source
from pub.models import Channel


class KeywordSerializer(serializers.ModelSerializer):
    locale_code = serializers.SlugRelatedField(source="locale", slug_field="code", read_only=True)

    class Meta:
        model = Keyword
        fields = ["id", "locale_code", "term", "normalized_term", "created_at"]


class MetricSerializer(serializers.ModelSerializer):
    keyword_id = serializers.PrimaryKeyRelatedField(source="keyword", read_only=True)
    source_code = serializers.SlugRelatedField(source="source", slug_field="code", read_only=True)

    class Meta:
        model = Metric
        fields = [
            "id",
            "keyword_id",
            "source_code",
            "planner_run_id",
            "month",
            "avg_searches",
            "competition",
            "cpc",
        ]


class PlannerRunSerializer(serializers.ModelSerializer):
    source_code = serializers.SlugRelatedField(source="source", slug_field="code", read_only=True)
    locale_code = serializers.SlugRelatedField(source="locale", slug_field="code", read_only=True)

    class Meta:
        model = PlannerRun
        fields = [
            "id",
            "source_code",
            "locale_code",
            "product_type_id",
            "channel_id",
            "country_code",
            "geo_target",
            "request_json",
            "status",
            "error_json",
            "started_at",
            "finished_at",
            "created_at",
        ]


class PlannerRunKeywordSerializer(serializers.ModelSerializer):
    keyword_term = serializers.CharField(source="keyword.term", read_only=True)

    class Meta:
        model = PlannerRunKeyword
        fields = [
            "id",
            "run_id",
            "keyword_id",
            "keyword_term",
            "seed_id",
            "concept",
            "status",
            "classifier",
            "confidence",
            "mapped_product_type_id",
            "mapped_attribute_id",
            "mapped_attribute_value_id",
            "reason_json",
            "created_at",
        ]


class PlannerRunCreateSerializer(serializers.Serializer):
    locale_code = serializers.CharField()
    product_type_id = serializers.IntegerField(required=False)
    channel_code = serializers.CharField(required=False, allow_blank=True)
    seed_terms = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    negative_terms = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    source_code = serializers.CharField(required=False, default="gads_keyword_planner")

    def validate_locale_code(self, value: str) -> str:
        if not Locale.objects.filter(code=value).exists():
            raise serializers.ValidationError("Unknown locale_code.")
        return value

    def validate_product_type_id(self, value: int) -> int:
        if not ProductType.objects.filter(id=value).exists():
            raise serializers.ValidationError("Unknown product_type_id.")
        return value

    def validate_channel_code(self, value: str) -> str:
        if value and not Channel.objects.filter(code=value, is_active=True).exists():
            raise serializers.ValidationError("Unknown or inactive channel_code.")
        return value

    def validate_source_code(self, value: str) -> str:
        if not Source.objects.filter(code=value).exists():
            Source.objects.create(code=value)
        return value


class PlannerSeedSerializer(serializers.ModelSerializer):
    locale_code = serializers.SlugRelatedField(source="locale", slug_field="code", read_only=True)
    channel_id = serializers.PrimaryKeyRelatedField(source="channel", read_only=True)

    class Meta:
        model = PlannerSeed
        fields = [
            "id",
            "locale_code",
            "term",
            "normalized_term",
            "seed_type",
            "is_active",
            "product_type_id",
            "channel_id",
            "created_at",
        ]
