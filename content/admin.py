from django.contrib import admin

from .models import (
    AttributeI18n,
    AttributeValueI18n,
    AttributeValueSynonym,
    ComplianceClaim,
    ContentBlock,
    Locale,
    ProductTypeSynonym,
    ProductTypeI18n,
    ProductI18n,
    ProductMedia,
    ProductAttributeValueI18n,
)


@admin.register(Locale)
class LocaleAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "created_at")
    search_fields = ("code", "name")


@admin.register(ProductI18n)
class ProductI18nAdmin(admin.ModelAdmin):
    list_display = ("product", "locale", "title", "slug")
    list_filter = ("locale",)
    search_fields = ("title", "slug", "product__id")


@admin.register(ProductAttributeValueI18n)
class ProductAttributeValueI18nAdmin(admin.ModelAdmin):
    list_display = ("product_attribute_value", "locale", "value_text")
    list_filter = ("locale",)
    search_fields = ("value_text", "product_attribute_value__product__id", "product_attribute_value__attribute__code")


@admin.register(AttributeI18n)
class AttributeI18nAdmin(admin.ModelAdmin):
    list_display = ("attribute", "locale", "label")
    list_filter = ("locale", "attribute")
    search_fields = ("label", "attribute__code")


@admin.register(AttributeValueI18n)
class AttributeValueI18nAdmin(admin.ModelAdmin):
    list_display = ("attribute_value", "locale", "label")
    list_filter = ("locale",)
    search_fields = ("label", "attribute_value__code")


@admin.register(AttributeValueSynonym)
class AttributeValueSynonymAdmin(admin.ModelAdmin):
    list_display = (
        "attribute_value",
        "locale",
        "channel",
        "term",
        "status",
        "score",
        "source",
        "keyword",
        "updated_at",
    )
    list_filter = ("locale", "channel", "status")
    search_fields = ("term", "attribute_value__code", "keyword__term")


@admin.register(ProductTypeI18n)
class ProductTypeI18nAdmin(admin.ModelAdmin):
    list_display = ("product_type", "locale", "label")
    list_filter = ("locale",)
    search_fields = ("product_type__code", "label")


@admin.register(ProductTypeSynonym)
class ProductTypeSynonymAdmin(admin.ModelAdmin):
    list_display = (
        "product_type",
        "locale",
        "channel",
        "term",
        "status",
        "is_active",
        "priority",
        "score",
        "source",
        "updated_at",
    )
    list_filter = ("locale", "channel", "status", "is_active", "source")
    search_fields = ("term", "product_type__code")
    ordering = ("product_type", "locale", "channel", "-priority", "-score", "term")


@admin.register(ContentBlock)
class ContentBlockAdmin(admin.ModelAdmin):
    list_display = ("product", "locale", "block_type", "sort_order", "created_at")
    list_filter = ("locale", "block_type")
    search_fields = ("product__id", "block_type")
    ordering = ("product_id", "locale_id", "sort_order", "id")


@admin.register(ProductMedia)
class ProductMediaAdmin(admin.ModelAdmin):
    list_display = ("product", "kind", "url", "sort_order", "created_at")
    list_filter = ("kind",)
    search_fields = ("product__id", "url")
    ordering = ("product_id", "sort_order", "id")


@admin.register(ComplianceClaim)
class ComplianceClaimAdmin(admin.ModelAdmin):
    list_display = ("product", "code", "value", "document_url", "created_at")
    search_fields = ("product__id", "code")
