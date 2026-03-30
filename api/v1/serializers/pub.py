from rest_framework import serializers

from catalog.models import Attribute, Product, ProductType, Variant
from content.models import Locale
from kw.models import PlannerRun
from pub.services.ai_constants import DEFAULT_DESCRIPTION_AI_MODEL, DESCRIPTION_AI_MODELS
from pub.models import (
    Channel,
    ChannelListing,
    ChannelListingMap,
    ChannelLocalePolicy,
    ChannelPolicySet,
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
from catalog.models import ChannelListingAxis
from catalog.services.axis_resolution import get_axes_for_context


class ChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Channel
        fields = ["id", "code", "name", "is_active", "priority", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_code(self, value):
        """Ensure code is unique (except for current instance on update)"""
        if self.instance and self.instance.code == value:
            return value
        if Channel.objects.filter(code=value).exists():
            raise serializers.ValidationError("A channel with this code already exists.")
        return value


class ChannelPolicySetSerializer(serializers.ModelSerializer):
    channel_code = serializers.CharField(source="channel.code", read_only=True)
    
    class Meta:
        model = ChannelPolicySet
        fields = ["id", "channel", "channel_code", "version", "status", "notes", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        """Ensure unique version per channel"""
        channel = attrs.get("channel") or (self.instance.channel if self.instance else None)
        version = attrs.get("version") or (self.instance.version if self.instance else None)
        
        if channel and version:
            existing = ChannelPolicySet.objects.filter(channel=channel, version=version)
            if self.instance:
                existing = existing.exclude(id=self.instance.id)
            if existing.exists():
                raise serializers.ValidationError(
                    {"version": f"A policy set with version {version} already exists for this channel."}
                )
        return attrs


class ChannelLocalePolicySerializer(serializers.ModelSerializer):
    channel_code = serializers.CharField(source="policy_set.channel.code", read_only=True)
    locale_code = serializers.CharField(source="locale.code", read_only=True)
    policy_set_id = serializers.IntegerField(write_only=True, required=False)
    locale_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = ChannelLocalePolicy
        fields = [
            "id",
            "policy_set",
            "policy_set_id",
            "channel_code",
            "locale",
            "locale_id",
            "locale_code",
            "country_code",
            "currency_code",
            "title_max_len",
            "meta_title_max_len",
            "meta_description_max_len",
            "description_max_len",
            "bullet_count",
            "bullet_max_len",
            "title_separator",
            "brand_position",
            "title_mode",
            "auto_create_selection",
            "auto_approve_selection",
            "selection_scope",
            "context",
            "normalize_whitespace",
            "dedupe_words",
            "banned_terms",
            "rules_json",
        ]
        read_only_fields = ["id"]
        extra_kwargs = {
            # policy_set and locale are supplied via policy_set_id / locale_id
            # write-only helper fields; mark the FK fields as not required so
            # DRF validation doesn't reject the request before create() runs.
            "policy_set": {"required": False},
            "locale": {"required": False},
        }

    def validate_title_max_len(self, value):
        if value < 1:
            raise serializers.ValidationError("Title max length must be at least 1.")
        if value > 500:
            raise serializers.ValidationError("Title max length cannot exceed 500.")
        return value

    def validate_meta_title_max_len(self, value):
        if value < 1:
            raise serializers.ValidationError("Meta title max length must be at least 1.")
        if value > 200:
            raise serializers.ValidationError("Meta title max length cannot exceed 200.")
        return value

    def validate_description_max_len(self, value):
        if value < 1:
            raise serializers.ValidationError("Description max length must be at least 1.")
        if value > 20000:
            raise serializers.ValidationError("Description max length cannot exceed 20000.")
        return value

    def validate_bullet_count(self, value):
        if value < 0:
            raise serializers.ValidationError("Bullet count cannot be negative.")
        if value > 20:
            raise serializers.ValidationError("Bullet count cannot exceed 20.")
        return value

    def validate_bullet_max_len(self, value):
        if value < 1:
            raise serializers.ValidationError("Bullet max length must be at least 1.")
        if value > 1000:
            raise serializers.ValidationError("Bullet max length cannot exceed 1000.")
        return value

    def validate(self, attrs):
        """Ensure policy_set and locale are resolvable before create/update."""
        from pub.models import ChannelPolicySet
        errors = {}

        policy_set_id = attrs.get("policy_set_id")
        if policy_set_id and not attrs.get("policy_set"):
            try:
                attrs["policy_set"] = ChannelPolicySet.objects.get(id=policy_set_id)
            except ChannelPolicySet.DoesNotExist:
                errors["policy_set_id"] = f"Policy set with id={policy_set_id} does not exist."

        locale_id = attrs.get("locale_id")
        if locale_id and not attrs.get("locale"):
            try:
                attrs["locale"] = Locale.objects.get(id=locale_id)
            except Locale.DoesNotExist:
                errors["locale_id"] = f"Locale with id={locale_id} does not exist."

        if not attrs.get("policy_set"):
            errors["policy_set_id"] = "A policy set is required. Select a channel and policy set."
        if not attrs.get("locale"):
            errors["locale_id"] = "A locale is required."

        if errors:
            raise serializers.ValidationError(errors)

        return attrs

    def create(self, validated_data):
        """Handle policy_set_id and locale_id if provided"""
        validated_data.pop("policy_set_id", None)
        validated_data.pop("locale_id", None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Handle policy_set_id and locale_id — already resolved in validate()"""
        validated_data.pop("policy_set_id", None)
        validated_data.pop("locale_id", None)
        return super().update(instance, validated_data)


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
    improve_title = serializers.BooleanField(required=False, default=False)
    title_ai_model = serializers.CharField(required=False, allow_blank=True, default=DEFAULT_DESCRIPTION_AI_MODEL)
    title_ai_instructions = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_title_ai_model(self, value: str) -> str:
        value = (value or "").strip() or DEFAULT_DESCRIPTION_AI_MODEL
        if value not in DESCRIPTION_AI_MODELS:
            raise serializers.ValidationError(
                f"Unsupported model '{value}'. Allowed: {', '.join(sorted(DESCRIPTION_AI_MODELS))}"
            )
        return value

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
    description_model = serializers.CharField(required=False, allow_blank=True, default=DEFAULT_DESCRIPTION_AI_MODEL)

    def validate_description_model(self, value: str) -> str:
        value = (value or "").strip() or DEFAULT_DESCRIPTION_AI_MODEL
        if value not in DESCRIPTION_AI_MODELS:
            raise serializers.ValidationError(
                f"Unsupported model '{value}'. Allowed: {', '.join(sorted(DESCRIPTION_AI_MODELS))}"
            )
        return value
    description_instructions = serializers.CharField(required=False, allow_blank=True, default="")

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


class SaveContentSelectionSerializer(serializers.Serializer):
    """Save current preview as a draft content selection (description + bullets)."""

    variant_id = serializers.IntegerField(min_value=1)
    locale_code = serializers.CharField()
    channel_code = serializers.CharField()
    context = serializers.CharField(required=False, default="title")
    description = serializers.CharField(allow_blank=True, default="")
    bullets = serializers.ListField(
        child=serializers.CharField(allow_blank=True),
        required=False,
        allow_empty=True,
        default=list,
    )

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
    batch_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)

    def validate_profile_id(self, value):
        if not ExportProfile.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Unknown or inactive profile_id.")
        return value

    def validate_batch_id(self, value):
        if value is not None and not GenerationBatch.objects.filter(id=value).exists():
            raise serializers.ValidationError("Unknown batch_id.")
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
    profile = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = ExportJob
        fields = [
            "id",
            "profile_id",
            "profile",
            "batch_id",
            "status",
            "file_url",
            "stats_json",
            "error_message",
            "started_at",
            "finished_at",
            "created_at",
        ]

    def get_profile(self, obj):
        try:
            return str(obj.profile)
        except Exception:
            return ""

    def get_file_url(self, obj):
        if not obj.result_file:
            return None
        request = self.context.get("request")
        url = f"/api/v1/exports/{obj.id}/download/"
        if request:
            return request.build_absolute_uri(url)
        return url


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


# ============================================================================
# Channel Listing (Group) Serializers
# ============================================================================


class ChannelListingSerializer(serializers.ModelSerializer):
    """Serializer for ChannelListing (marketplace listing groups)."""
    
    product_code = serializers.SerializerMethodField()
    channel_code = serializers.CharField(source="channel.code", read_only=True)
    locale_code = serializers.CharField(source="locale.code", read_only=True, allow_null=True)
    variant_count = serializers.SerializerMethodField()
    
    def get_product_code(self, obj):
        return obj.product.code if obj.product else None

    class Meta:
        model = ChannelListing
        fields = [
            "id",
            "product_id",
            "product_code",
            "channel_id",
            "channel_code",
            "locale_id",
            "locale_code",
            "name",
            "is_default",
            "variant_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_variant_count(self, obj):
        return getattr(obj, "variant_count", None) or ChannelListingMap.objects.filter(listing=obj).count()


class ChannelListingCreateSerializer(serializers.Serializer):
    """Serializer for creating a new ChannelListing."""
    
    product_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    channel_id = serializers.IntegerField(min_value=1)
    locale_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    name = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    is_default = serializers.BooleanField(required=False, default=True)

    def validate_product_id(self, value):
        if value is None:
            return value
        if not Product.objects.filter(id=value).exists():
            raise serializers.ValidationError("Unknown product_id.")
        return value

    def validate_channel_id(self, value):
        if not Channel.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Unknown or inactive channel_id.")
        return value

    def validate_locale_id(self, value):
        if value is None:
            return value
        if not Locale.objects.filter(id=value).exists():
            raise serializers.ValidationError("Unknown locale_id.")
        return value


class MoveVariantsSerializer(serializers.Serializer):
    """Serializer for moving variants to a listing."""
    
    variant_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )

    def validate_variant_ids(self, value):
        variants = Variant.objects.filter(id__in=value)
        if len(value) != variants.count():
            known = {v.id for v in variants}
            missing = [vid for vid in value if vid not in known]
            raise serializers.ValidationError(f"Unknown variant_ids: {', '.join(str(v) for v in missing)}")
        return value


class RemoveVariantsSerializer(serializers.Serializer):
    """Serializer for removing variants from a listing."""
    
    variant_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )


class ListingAxisSerializer(serializers.Serializer):
    """Serializer for a single axis definition."""
    
    attribute_id = serializers.IntegerField(min_value=1)
    position = serializers.IntegerField(min_value=0, required=False, default=0)
    label_override = serializers.CharField(max_length=200, required=False, allow_blank=True, allow_null=True)
    enabled = serializers.BooleanField(required=False, default=True)

    def validate_attribute_id(self, value):
        from catalog.models import Attribute
        if not Attribute.objects.filter(id=value).exists():
            raise serializers.ValidationError(f"Unknown attribute_id: {value}")
        return value


class SetListingAxesSerializer(serializers.Serializer):
    """Serializer for setting listing axes."""
    
    axes = serializers.ListField(
        child=ListingAxisSerializer(),
        allow_empty=True,
    )


class ChannelListingAxisSerializer(serializers.ModelSerializer):
    """Serializer for ChannelListingAxis read operations."""
    
    attribute_code = serializers.CharField(source="attribute.code", read_only=True)

    class Meta:
        model = ChannelListingAxis
        fields = [
            "id",
            "listing_id",
            "attribute_id",
            "attribute_code",
            "position",
            "label_override",
            "enabled",
            "created_at",
        ]


class ChannelListingDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for ChannelListing with variants and axes."""
    
    product_code = serializers.SerializerMethodField()
    product_type_id = serializers.SerializerMethodField()
    channel_code = serializers.CharField(source="channel.code", read_only=True)
    locale_code = serializers.SerializerMethodField()
    variants = serializers.SerializerMethodField()
    axes = serializers.SerializerMethodField()
    variant_count = serializers.SerializerMethodField()
    
    def get_product_code(self, obj):
        return obj.product.code if obj.product else None

    def get_product_type_id(self, obj):
        return obj.product.product_type_id if obj.product else None

    class Meta:
        model = ChannelListing
        fields = [
            "id",
            "product_id",
            "product_code",
            "product_type_id",
            "channel_id",
            "channel_code",
            "locale_id",
            "locale_code",
            "name",
            "is_default",
            "variants",
            "variant_count",
            "axes",
            "created_at",
            "updated_at",
        ]

    def get_locale_code(self, obj):
        return obj.locale.code if obj.locale else None

    def get_variants(self, obj):
        maps = ChannelListingMap.objects.filter(listing=obj).select_related("variant")
        return [
            {
                "id": m.variant.id,
                "sku": m.variant.sku,
                "barcode": m.variant.barcode,
                "external_id": m.external_id,
                "sync_status": m.sync_status,
            }
            for m in maps
        ]

    def get_axes(self, obj):
        if obj.product_id:
            resolved = get_axes_for_context(obj.product, channel=obj.channel, listing=obj)
            return [
                {
                    "attribute_id": a.attribute_id,
                    "attribute_code": a.attribute_code,
                    "position": a.position,
                    "label_override": a.label_override,
                }
                for a in resolved
            ]
        axes = ChannelListingAxis.objects.filter(listing=obj).select_related("attribute").order_by("position")
        return [
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

    def get_variant_count(self, obj):
        return ChannelListingMap.objects.filter(listing=obj).count()
