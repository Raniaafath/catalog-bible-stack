from django.contrib import admin

from .models import (
    AttributeMapping,
    CategoryBatch,
    ImportColumnMap,
    ImportRow,
    ProductImport,
)


@admin.register(ProductImport)
class ProductImportAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "original_filename", "row_count", "error_count", "created_at")
    list_filter = ("status",)
    search_fields = ("id", "original_filename", "created_by")


@admin.register(ImportColumnMap)
class ImportColumnMapAdmin(admin.ModelAdmin):
    list_display = ("product_import", "created_at")
    search_fields = ("product_import__id",)


@admin.register(ImportRow)
class ImportRowAdmin(admin.ModelAdmin):
    list_display = ("product_import", "row_number", "is_valid")
    list_filter = ("is_valid",)
    search_fields = ("product_import__id",)


@admin.register(CategoryBatch)
class CategoryBatchAdmin(admin.ModelAdmin):
    list_display = ("id", "category", "status", "product_count", "variant_count", "created_at")
    list_filter = ("status",)
    search_fields = ("category",)


@admin.register(AttributeMapping)
class AttributeMappingAdmin(admin.ModelAdmin):
    list_display = ("category_batch", "source_attr_name", "strategy", "target_attribute")
    list_filter = ("strategy",)
    search_fields = ("source_attr_name",)
