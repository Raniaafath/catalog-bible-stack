from rest_framework import serializers

from catalog.models import Attribute, Product, ProductType, Variant
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
    GenerationOutput,
    GenerationRun,
    Template,
    TemplatePart,
)


class TemplateSerializer(serializers.ModelSerializer):
    product_type_id = serializers.PrimaryKeyRelatedField(
        source="product_type",
        queryset=ProductType.objects.all(),
    )
    locale_code = serializers.SlugRelatedField(
        source="locale",
        slug_field="code",
        queryset=Locale.objects.all(),
    )
    channel_code = serializers.SlugRelatedField(
        source="channel",
        slug_field="code",
        queryset=Channel.objects.filter(is_active=True),
    )

    class Meta:
        model = Template
        fields = [
            "id",
            "product_type_id",
            "locale_code",
            "channel_code",
            "kind",
            "version",
            "status",
        ]


class TemplatePartSerializer(serializers.ModelSerializer):
    template_id = serializers.PrimaryKeyRelatedField(
        source="template",
        queryset=Template.objects.all(),
    )
    attribute_id = serializers.PrimaryKeyRelatedField(
        source="attribute",
        queryset=Attribute.objects.all(),
        allow_null=True,
        required=False,
    )

    class Meta:
        model = TemplatePart
        fields = [
            "id",
            "template_id",
            "position",
            "part_type",
            "attribute_id",
            "keyword_role",
            "literal_text",
            "required",
        ]

    def validate(self, attrs):
        part_type = attrs.get("part_type")
        literal_text = attrs.get("literal_text")
        keyword_role = attrs.get("keyword_role")
        attribute = attrs.get("attribute")

        if part_type == TemplatePart.PartType.LITERAL and not literal_text:
            raise serializers.ValidationError({"literal_text": "Literal parts require literal_text."})
        if part_type in {
            TemplatePart.PartType.ATTRIBUTE_VALUE,
            TemplatePart.PartType.AXIS_ATTRIBUTE,
        } and not attribute:
            raise serializers.ValidationError({"attribute_id": "Attribute parts require attribute_id."})
        if part_type == TemplatePart.PartType.KEYWORD and not keyword_role:
            raise serializers.ValidationError({"keyword_role": "Keyword parts require keyword_role."})

        return attrs


class TitleGenerateRequestSerializer(serializers.Serializer):
    variant_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )
    locale_code = serializers.CharField()
    channel_code = serializers.CharField()
    planner_run_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    include_descriptions = serializers.BooleanField(required=False, default=False)
    title_mode_override = serializers.ChoiceField(
        choices=["auto", "review"],
        required=False,
        allow_null=True,
    )
    context = serializers.CharField(required=False, default="title")

    def validate_locale_code(self, value: str) -> str:
        if not Locale.objects.filter(code=value).exists():
            raise serializers.ValidationError("Unknown locale_code.")
        return value

    def validate_channel_code(self, value: str) -> str:
        if not Channel.objects.filter(code=value, is_active=True).exists():
            raise serializers.ValidationError("Unknown or inactive channel_code.")
        return value

    def validate_variant_ids(self, value):
        variants = Variant.objects.filter(id__in=value)
        if len(value) != variants.count():
            known = {variant.id for variant in variants}
            missing = [variant_id for variant_id in value if variant_id not in known]
            raise serializers.ValidationError(f"Unknown variant_ids: {', '.join(str(v) for v in missing)}")
        return value

    def validate_planner_run_id(self, value):
        if value is None:
            return value
        if not PlannerRun.objects.filter(id=value).exists():
            raise serializers.ValidationError("Unknown planner_run_id.")
        return value


class TitleSuggestionsQuerySerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1, required=False)
    variant_id = serializers.IntegerField(min_value=1, required=False)
    locale_code = serializers.CharField()
    channel_code = serializers.CharField()
    context = serializers.CharField(required=False, default="title")
    planner_run_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    limit_head = serializers.IntegerField(min_value=0, required=False)
    limit_hook = serializers.IntegerField(min_value=0, required=False)
    include_explanations = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        product_id = attrs.get("product_id")
        variant_id = attrs.get("variant_id")
        if not product_id and not variant_id:
            raise serializers.ValidationError("Provide product_id or variant_id.")
        if product_id and not Product.objects.filter(id=product_id).exists():
            raise serializers.ValidationError("Unknown product_id.")
        if variant_id and not Variant.objects.filter(id=variant_id).exists():
            raise serializers.ValidationError("Unknown variant_id.")
        return attrs

    def validate_locale_code(self, value: str) -> str:
        if not Locale.objects.filter(code=value).exists():
            raise serializers.ValidationError("Unknown locale_code.")
        return value


class ContentPreviewRequestSerializer(serializers.Serializer):
    variant_id = serializers.IntegerField(min_value=1)
    locale_code = serializers.CharField()
    channel_code = serializers.CharField()
    planner_run_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    context = serializers.CharField(required=False, default="title")
    include_descriptions = serializers.BooleanField(required=False, default=False)

    def validate_locale_code(self, value: str) -> str:
        if not Locale.objects.filter(code=value).exists():
            raise serializers.ValidationError("Unknown locale_code.")
        return value

    def validate_channel_code(self, value: str) -> str:
        if not Channel.objects.filter(code=value, is_active=True).exists():
            raise serializers.ValidationError("Unknown or inactive channel_code.")
        return value

    def validate_variant_id(self, value):
        if not Variant.objects.filter(id=value).exists():
            raise serializers.ValidationError("Unknown variant_id.")
        return value

    def validate_planner_run_id(self, value):
        if value is None:
            return value
        if not PlannerRun.objects.filter(id=value).exists():
            raise serializers.ValidationError("Unknown planner_run_id.")
        return value


class ContentGenerateRequestSerializer(serializers.Serializer):
    variant_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )
    locale_code = serializers.CharField()
    channel_code = serializers.CharField()
    planner_run_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    include_descriptions = serializers.BooleanField(required=False, default=False)
    title_mode_override = serializers.ChoiceField(
        choices=["auto", "review"],
        required=False,
        allow_null=True,
    )
    context = serializers.CharField(required=False, default="title")

    def validate_locale_code(self, value: str) -> str:
        if not Locale.objects.filter(code=value).exists():
            raise serializers.ValidationError("Unknown locale_code.")
        return value

    def validate_channel_code(self, value: str) -> str:
        if not Channel.objects.filter(code=value, is_active=True).exists():
            raise serializers.ValidationError("Unknown or inactive channel_code.")
        return value

    def validate_variant_ids(self, value):
        variants = Variant.objects.filter(id__in=value)
        if len(value) != variants.count():
            known = {variant.id for variant in variants}
            missing = [variant_id for variant_id in value if variant_id not in known]
            raise serializers.ValidationError(f"Unknown variant_ids: {', '.join(str(v) for v in missing)}")
        return value

    def validate_planner_run_id(self, value):
        if value is None:
            return value
        if not PlannerRun.objects.filter(id=value).exists():
            raise serializers.ValidationError("Unknown planner_run_id.")
        return value


class GenerationBatchCreateSerializer(serializers.Serializer):
    content_set_id = serializers.IntegerField(min_value=1, required=False)
    variant_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        allow_empty=True,
    )
    product_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        allow_empty=True,
    )
    locale_code = serializers.CharField()
    channel_code = serializers.CharField()
    context = serializers.CharField(required=False, default="content")
    planner_run_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    mode = serializers.ChoiceField(choices=["auto", "review"], required=False, default="auto")
    include_descriptions = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        if not attrs.get("content_set_id") and not attrs.get("variant_ids") and not attrs.get("product_ids"):
            raise serializers.ValidationError("Provide content_set_id, variant_ids, or product_ids.")
        return attrs

    def validate_content_set_id(self, value):
        if not ContentSet.objects.filter(id=value).exists():
            raise serializers.ValidationError("Unknown content_set_id.")
        return value

    def validate_locale_code(self, value: str) -> str:
        if not Locale.objects.filter(code=value).exists():
            raise serializers.ValidationError("Unknown locale_code.")
        return value

    def validate_channel_code(self, value: str) -> str:
        if not Channel.objects.filter(code=value, is_active=True).exists():
            raise serializers.ValidationError("Unknown or inactive channel_code.")
        return value

    def validate_planner_run_id(self, value):
        if value is None:
            return value
        if not PlannerRun.objects.filter(id=value).exists():
            raise serializers.ValidationError("Unknown planner_run_id.")
        return value


class ExportJobCreateSerializer(serializers.Serializer):
    profile_id = serializers.IntegerField(min_value=1)
    batch_id = serializers.IntegerField(min_value=1)

    def validate_profile_id(self, value):
        if not ExportProfile.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Unknown or inactive profile_id.")
        return value

    def validate_batch_id(self, value):
        if not GenerationBatch.objects.filter(id=value).exists():
            raise serializers.ValidationError("Unknown batch_id.")
        return value

    def validate_channel_code(self, value: str) -> str:
        if not Channel.objects.filter(code=value, is_active=True).exists():
            raise serializers.ValidationError("Unknown or inactive channel_code.")
        return value

    def validate_planner_run_id(self, value):
        if value is None:
            return value
        if not PlannerRun.objects.filter(id=value).exists():
            raise serializers.ValidationError("Unknown planner_run_id.")
        return value


class GenerationOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = GenerationOutput
        fields = ["id", "field", "position", "text", "score_json", "created_at"]


class ContentSetSerializer(serializers.ModelSerializer):
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = ContentSet
        fields = [
            "id",
            "name",
            "description",
            "channel_id",
            "locale_id",
            "context",
            "kind",
            "filter_json",
            "created_at",
            "updated_at",
            "item_count",
        ]

    def get_item_count(self, obj):
        return getattr(obj, "items_count", None) or obj.items.count()


class ContentSetItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentSetItem
        fields = ["id", "content_set_id", "product_id", "variant_id"]
        extra_kwargs = {
            "content_set_id": {"read_only": True},
        }


class GenerationBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = GenerationBatch
        fields = [
            "id",
            "content_set_id",
            "channel_id",
            "locale_id",
            "context",
            "planner_run_id",
            "mode",
            "include_descriptions",
            "status",
            "total",
            "generated",
            "needs_approval",
            "errors",
            "started_at",
            "finished_at",
            "created_at",
        ]


class GenerationBatchItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = GenerationBatchItem
        fields = [
            "id",
            "batch_id",
            "product_id",
            "variant_id",
            "status",
            "error_message",
            "generation_run_id",
            "selection_id",
            "preview_json",
            "created_at",
        ]


class ExportProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExportProfile
        fields = [
            "id",
            "name",
            "channel_id",
            "context",
            "format",
            "version",
            "columns_json",
            "options_json",
            "is_active",
            "created_at",
        ]


class ExportJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExportJob
        fields = [
            "id",
            "profile_id",
            "batch_id",
            "status",
            "result_file",
            "stats_json",
            "error_message",
            "started_at",
            "finished_at",
            "created_at",
        ]


class GenerationRunSerializer(serializers.ModelSerializer):
    outputs = GenerationOutputSerializer(many=True, read_only=True)
    status = serializers.SerializerMethodField()

    class Meta:
        model = GenerationRun
        fields = [
            "id",
            "product_id",
            "variant_id",
            "planner_run_id",
            "batch_id",
            "locale_id",
            "channel_id",
            "template_id",
            "model_info",
            "created_at",
            "outputs",
            "status",
        ]

    def get_status(self, obj):
        return "completed"
