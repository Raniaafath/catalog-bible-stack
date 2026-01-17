from django.contrib import admin

from .models import (
    Attribute,
    AttributeValue,
    BundleComponent,
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


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "product_type", "status", "brand", "model", "created_at", "updated_at")
    search_fields = ("code", "brand", "model")
    list_filter = ("product_type", "status")


@admin.register(Variant)
class VariantAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "sku", "barcode", "axis_signature", "created_at")
    search_fields = ("sku", "barcode")
    list_filter = ("product",)


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


@admin.register(BundleComponent)
class BundleComponentAdmin(admin.ModelAdmin):
    list_display = ("bundle_variant", "component_variant", "quantity")
    list_filter = ("bundle_variant",)
