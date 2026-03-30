from django.contrib import admin

from .models import (
    Approval,
    Channel,
    ChannelBundlePolicy,
    ChannelConstraintPolicy,
    ChannelListing,
    ChannelListingMap,
    ChannelLocalePolicy,
    ContentSelection,
    ChannelPolicySet,
    ChannelProductOption,
    ChannelProductOptionAttribute,
    ChannelProductOptionI18n,
    GenerationOutput,
    GenerationRun,
    TitleSelection,
    Template,
    TemplatePart,
)


class TemplatePartInline(admin.TabularInline):
    model = TemplatePart
    extra = 1


class ChannelPolicySetInline(admin.TabularInline):
    model = ChannelPolicySet
    extra = 0


class ChannelLocalePolicyInline(admin.TabularInline):
    model = ChannelLocalePolicy
    extra = 0


class ChannelConstraintPolicyInline(admin.StackedInline):
    model = ChannelConstraintPolicy
    extra = 0
    max_num = 1


class ChannelBundlePolicyInline(admin.StackedInline):
    model = ChannelBundlePolicy
    extra = 0
    max_num = 1


class ChannelProductOptionI18nInline(admin.TabularInline):
    model = ChannelProductOptionI18n
    extra = 0


class ChannelProductOptionAttributeInline(admin.TabularInline):
    model = ChannelProductOptionAttribute
    extra = 0


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active", "priority", "created_at")
    search_fields = ("code", "name")
    inlines = [ChannelPolicySetInline]


@admin.register(ChannelPolicySet)
class ChannelPolicySetAdmin(admin.ModelAdmin):
    list_display = ("channel", "version", "status", "created_at")
    list_filter = ("status", "channel")
    search_fields = ("channel__code",)
    inlines = [ChannelLocalePolicyInline, ChannelConstraintPolicyInline, ChannelBundlePolicyInline]


@admin.register(ChannelProductOption)
class ChannelProductOptionAdmin(admin.ModelAdmin):
    list_display = ("product", "channel", "slot_index", "option_kind", "code", "created_at")
    list_filter = ("channel", "option_kind")
    search_fields = ("product__id", "channel__code", "code")
    inlines = [ChannelProductOptionI18nInline, ChannelProductOptionAttributeInline]


@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ("product_type", "locale", "channel", "kind", "version", "status", "created_at")
    list_filter = ("product_type", "locale", "channel", "kind", "status")
    search_fields = ("product_type__code", "channel__code")
    inlines = [TemplatePartInline]


@admin.register(TemplatePart)
class TemplatePartAdmin(admin.ModelAdmin):
    list_display = (
        "template",
        "position",
        "part_type",
        "attribute",
        "keyword_role",
        "required",
        "created_at",
    )
    list_filter = ("part_type", "keyword_role")
    search_fields = ("template__id", "attribute__code")


@admin.register(GenerationRun)
class GenerationRunAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "variant", "locale", "channel", "template", "created_at")
    list_filter = ("locale", "channel")
    search_fields = ("product__id", "variant__id", "template__id")


@admin.register(GenerationOutput)
class GenerationOutputAdmin(admin.ModelAdmin):
    list_display = ("run", "field", "created_at")
    search_fields = ("run__id", "field")


@admin.register(TitleSelection)
class TitleSelectionAdmin(admin.ModelAdmin):
    list_display = ("product", "variant", "locale", "channel", "planner_run", "status", "updated_at")
    list_filter = ("status", "locale", "channel")
    search_fields = ("product__id", "variant__id", "head_text", "hook_text")


@admin.register(Approval)
class ApprovalAdmin(admin.ModelAdmin):
    list_display = ("entity_type", "entity_id", "status", "approved_by", "approved_at", "created_at")
    list_filter = ("status",)
    search_fields = ("entity_type", "entity_id")


@admin.register(ContentSelection)
class ContentSelectionAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "variant", "locale", "channel", "context", "status", "created_by_type", "updated_at")
    list_filter = ("status", "locale", "channel", "created_by_type")
    search_fields = ("product__code", "variant__sku", "locale__code", "channel__code", "description_text")
    raw_id_fields = ("product", "variant", "locale", "channel", "planner_run")
    readonly_fields = ("created_at", "updated_at")
    list_per_page = 50


@admin.register(ChannelListing)
class ChannelListingAdmin(admin.ModelAdmin):
    list_display = ("product", "channel", "locale", "name", "is_default", "created_at")
    list_filter = ("channel", "locale", "is_default")
    search_fields = ("product__code", "channel__code", "name")
    raw_id_fields = ("product", "locale")


@admin.register(ChannelListingMap)
class ChannelListingMapAdmin(admin.ModelAdmin):
    list_display = ("variant", "listing", "channel", "external_id", "sync_status", "last_sync_at")
    list_filter = ("channel", "sync_status", "listing")
    search_fields = ("variant__id", "channel__code", "external_id", "listing__name")
    raw_id_fields = ("listing", "variant")
