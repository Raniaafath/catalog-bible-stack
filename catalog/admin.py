from django.contrib import admin

from .models import (
    Attribute,
    AttributeValue,
    BundleComponent,
    ChannelListingAxis,
    ChannelVariantAxis,
    Product,
    ProductAttributeValue,
    ProductType,
    ProductTypeAttribute,
    ProductVariantAxis,
    Variant,
)


@admin.register(ProductType)
class ProductTypeAdmin(admin.ModelAdmin):
    list_display = ("code", "is_active", "sort_order", "parent", "main_category", "category_path", "created_at")
    search_fields = ("code", "default_label", "main_category", "category_path")
    list_filter = ("is_active",)


class VariantInline(admin.TabularInline):
    """Inline editing for variants within Product admin"""
    model = Variant
    extra = 1
    fields = ("sku", "barcode", "mpn", "source_title", "axis_signature")
    readonly_fields = ("internal_sku",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "product_type", "status", "brand", "model", "variants_count", "created_at", "updated_at")
    search_fields = ("code", "brand", "model", "default_label")
    list_filter = ("product_type", "status", "created_at")
    inlines = [VariantInline]
    
    def variants_count(self, obj):
        """Display number of variants for this product"""
        return obj.variants.count()
    variants_count.short_description = "Variants"


@admin.register(Variant)
class VariantAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "sku", "barcode", "mpn", "source_title", "axis_signature", "created_at")
    search_fields = ("sku", "barcode", "mpn", "source_title", "source_sku", "product__code", "product__brand")
    list_filter = ("product", "product__product_type", "created_at")
    readonly_fields = ("internal_sku",)
    fieldsets = (
        ("Product Link", {
            "fields": ("product",)
        }),
        ("Variant Information", {
            "fields": ("sku", "internal_sku", "barcode", "mpn", "axis_signature")
        }),
        ("Source Data (from import/supplier)", {
            "fields": ("source_title", "source_description", "source_sku", "source_supplier", "source_locale"),
            "classes": ("collapse",)
        }),
        ("Timestamps", {
            "fields": ("created_at",),
            "classes": ("collapse",)
        }),
    )


@admin.register(Attribute)
class AttributeAdmin(admin.ModelAdmin):
    list_display = ("code", "data_type", "is_multi", "created_at")
    search_fields = ("code",)
    list_filter = ("data_type", "is_multi")


@admin.register(AttributeValue)
class AttributeValueAdmin(admin.ModelAdmin):
    list_display = ("attribute", "code", "sort_order")
    search_fields = ("code", "attribute__code")
    list_filter = ("attribute",)


@admin.register(ProductTypeAttribute)
class ProductTypeAttributeAdmin(admin.ModelAdmin):
    list_display = ("product_type", "attribute", "required", "filterable", "variant_level")
    list_filter = ("product_type", "attribute", "required", "variant_level")


@admin.register(ProductAttributeValue)
class ProductAttributeValueAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "variant", "attribute", "attribute_value")
    list_filter = ("attribute",)
    search_fields = ("product__id", "variant__id", "attribute__code")


@admin.register(ProductVariantAxis)
class ProductVariantAxisAdmin(admin.ModelAdmin):
    list_display = ("product", "attribute", "position")
    list_filter = ("product",)


@admin.register(ChannelVariantAxis)
class ChannelVariantAxisAdmin(admin.ModelAdmin):
    list_display = ("product", "channel", "attribute", "position", "created_at")
    list_filter = ("channel", "product__product_type")
    search_fields = ("product__code", "channel__code", "attribute__code")
    ordering = ("product", "channel", "position")


@admin.register(ChannelListingAxis)
class ChannelListingAxisAdmin(admin.ModelAdmin):
    list_display = ("listing", "attribute", "position", "enabled", "created_at")
    list_filter = ("listing__channel", "enabled", "attribute")
    search_fields = ("listing__product__code", "listing__channel__code", "attribute__code")
    raw_id_fields = ("listing",)
    ordering = ("listing", "position")


@admin.register(BundleComponent)
class BundleComponentAdmin(admin.ModelAdmin):
    list_display = ("bundle_variant", "component_variant", "quantity")
    list_filter = ("bundle_variant",)
