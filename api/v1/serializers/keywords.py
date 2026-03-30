from rest_framework import serializers

from catalog.models import ProductType
from content.models import Locale
from kw.models import AttributeMap, Keyword, Metric, PlannerRun, PlannerRunKeyword, PlannerSeed, ProductKeywordMap, Source
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
    product_type_code = serializers.SlugRelatedField(source="product_type", slug_field="code", read_only=True, allow_null=True)
    keyword_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = PlannerRun
        fields = [
            "id",
            "source_code",
            "locale_code",
            "locale_id",
            "product_type_id",
            "product_type_code",
            "channel_id",
            "country_code",
            "geo_target",
            "request_json",
            "status",
            "error_json",
            "started_at",
            "finished_at",
            "created_at",
            "keyword_count",
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


class KeywordPlannerRunImportCsvSerializer(serializers.Serializer):
    locale_code = serializers.CharField()
    channel_code = serializers.CharField()
    product_type_id = serializers.IntegerField(required=False, allow_null=True)
    run_id = serializers.IntegerField(required=False, allow_null=True)
    source_code = serializers.CharField(required=False, default="google_ads")
    month = serializers.CharField(required=False, allow_blank=True)
    delimiter = serializers.CharField(required=False, default=",")

    def validate_locale_code(self, value: str) -> str:
        if not Locale.objects.filter(code=value).exists():
            raise serializers.ValidationError("Unknown locale_code.")
        return value

    def validate_channel_code(self, value: str) -> str:
        if not Channel.objects.filter(code=value, is_active=True).exists():
            raise serializers.ValidationError("Unknown or inactive channel_code.")
        return value

    def validate_product_type_id(self, value):
        if value is not None and not ProductType.objects.filter(id=value).exists():
            raise serializers.ValidationError("Unknown product_type_id.")
        return value


class RunAttributeMapSerializer(serializers.ModelSerializer):
    """Read serializer for AttributeMap in the context of a planner run."""

    keyword_id = serializers.PrimaryKeyRelatedField(source="keyword", read_only=True)
    keyword_term = serializers.CharField(source="keyword.term", read_only=True)
    attribute_code = serializers.SlugRelatedField(source="attribute", slug_field="code", read_only=True)
    attribute_value_id = serializers.PrimaryKeyRelatedField(source="attribute_value", read_only=True)
    attribute_value_code = serializers.SlugRelatedField(
        source="attribute_value", slug_field="code", read_only=True, allow_null=True
    )

    class Meta:
        model = AttributeMap
        fields = [
            "id",
            "keyword_id",
            "keyword_term",
            "attribute_code",
            "attribute_value_id",
            "attribute_value_code",
            "confidence",
            "status",
            "tagged_by",
            "reason_code",
            "evidence",
            "updated_at",
        ]


class RunAttributeMapUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[AttributeMap.Status.APPROVED, AttributeMap.Status.REJECTED])


class ProductKeywordMapSerializer(serializers.ModelSerializer):
    keyword_term = serializers.CharField(source="keyword.term", read_only=True)
    product_id = serializers.IntegerField(source="product.id", read_only=True)
    attribute_code = serializers.CharField(source="attribute.code", read_only=True, allow_null=True)
    attribute_name = serializers.SerializerMethodField()
    attribute_value_label = serializers.SerializerMethodField()
    attribute_value_code = serializers.CharField(source="attribute_value.code", read_only=True, allow_null=True)

    def get_attribute_name(self, obj):
        if not obj.attribute_id or not obj.attribute:
            return None
        return getattr(obj.attribute, "name", None) or obj.attribute.code

    def get_attribute_value_label(self, obj):
        if not obj.attribute_value_id or not obj.attribute_value:
            return None
        return getattr(obj.attribute_value, "label", None) or obj.attribute_value.code

    class Meta:
        model = ProductKeywordMap
        fields = [
            "id",
            "product_id",
            "keyword_term",
            "source",
            "match_kind",
            "matched_text",
            "confidence",
            "attribute_code",
            "attribute_name",
            "attribute_value_label",
            "attribute_value_code",
            "num_value",
            "num_unit",
            "evidence",
            "created_at",
        ]


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
