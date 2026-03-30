import json

from django.contrib import admin, messages
from django.core.management import call_command
from django.utils.html import format_html

from .models import (
    ImportColumnMapping,
    CategoryBatch,
    ImportColumnMap,
    ImportColumnRule,
    ImportRow,
    ProductImport,
)


def _run_cmd(request, label, cmd, **kwargs):
    try:
        call_command(cmd, **kwargs)
        messages.success(request, f"{label}: OK")
    except Exception as exc:
        messages.error(request, f"{label}: FAIL — {exc}")


@admin.action(description="Parse selected imports")
def parse_imports(modeladmin, request, queryset):
    for obj in queryset:
        _run_cmd(request, f"Parse import {obj.pk}", "import_parse", import_id=obj.pk)


@admin.action(description="Map attributes for selected imports")
def map_imports(modeladmin, request, queryset):
    for obj in queryset:
        _run_cmd(request, f"Map import {obj.pk}", "import_map", import_id=obj.pk)


@admin.action(description="Export selected imports (XLSX)")
def export_imports_xlsx(modeladmin, request, queryset):
    for obj in queryset:
        _run_cmd(request, f"Export import {obj.pk}", "import_export", import_id=obj.pk, format="xlsx")


@admin.action(description="Export selected imports (CSV)")
def export_imports_csv(modeladmin, request, queryset):
    for obj in queryset:
        _run_cmd(request, f"Export import {obj.pk}", "import_export", import_id=obj.pk, format="csv")


@admin.action(description="Initialize column mapping (rebuild rules from headers)")
def init_mapping(modeladmin, request, queryset):
    from importer.services import init_column_rules_for_import

    for obj in queryset:
        colmap = ImportColumnMap.objects.filter(product_import=obj).first()
        columns = (colmap.mapping_json or {}).get("columns", []) if colmap else []
        if not columns:
            messages.warning(request, f"Import {obj.pk}: no headers found (parse first).")
            continue
        init_column_rules_for_import(obj, columns, reset=True)
        messages.success(request, f"Import {obj.pk}: column mapping initialized.")


class ImportColumnRuleInline(admin.TabularInline):
    model = ImportColumnRule
    extra = 0
    can_delete = False
    fields = (
        "position",
        "column_name",
        "role",
        "target_attribute_code",
        "create_attribute_name",
        "attribute_type",
        "unit",
        "required",
    )
    readonly_fields = ("position", "column_name")
    ordering = ("position",)


class ImportRowInline(admin.TabularInline):
    model = ImportRow
    extra = 0
    can_delete = False
    fields = ("row_number", "is_valid", "errors_pretty", "raw_pretty")
    readonly_fields = fields
    show_change_link = True

    def errors_pretty(self, obj):
        if not obj.errors:
            return "-"
        text = json.dumps(obj.errors, ensure_ascii=True, indent=2)
        return format_html("<pre style='white-space:pre-wrap;margin:0'>{}</pre>", text)

    def raw_pretty(self, obj):
        text = json.dumps(obj.raw, ensure_ascii=True, indent=2)
        return format_html("<pre style='white-space:pre-wrap;margin:0'>{}</pre>", text)

    errors_pretty.short_description = "Errors"
    raw_pretty.short_description = "Raw"


@admin.register(ProductImport)
class ProductImportAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "original_filename", "file_type", "group_by_product_key", "row_count", "error_count", "created_by", "created_at")
    list_filter = ("status", "file_type", "group_by_product_key", "created_at")
    search_fields = ("id", "original_filename", "created_by")
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"
    actions = [parse_imports, map_imports, export_imports_xlsx, export_imports_csv, init_mapping]
    inlines = [ImportColumnRuleInline, ImportRowInline]
    fieldsets = (
        ("File Information", {
            "fields": ("source_file", "original_filename", "file_type", "status")
        }),
        ("Import Settings", {
            "fields": ("group_by_product_key",),
            "description": "Control whether variants with the same PRODUCT_KEY should be grouped into one Product.",
        }),
        ("Statistics", {
            "fields": ("row_count", "error_count", "created_by", "created_at"),
            "classes": ("collapse",)
        }),
    )


@admin.register(ImportColumnMap)
class ImportColumnMapAdmin(admin.ModelAdmin):
    list_display = ("product_import", "created_at")
    search_fields = ("product_import__id",)
    readonly_fields = ("created_at",)
    list_select_related = ("product_import",)


@admin.register(ImportRow)
class ImportRowAdmin(admin.ModelAdmin):
    list_display = ("product_import", "row_number", "is_valid", "has_errors")
    list_filter = ("is_valid", "product_import")
    search_fields = ("product_import__id", "row_number")
    readonly_fields = ("raw", "normalized", "errors")
    list_select_related = ("product_import",)

    @admin.display(boolean=True, description="Errors")
    def has_errors(self, obj):
        return bool(obj.errors)


@admin.register(CategoryBatch)
class CategoryBatchAdmin(admin.ModelAdmin):
    list_display = ("id", "product_import", "category", "status", "product_count", "variant_count", "created_at")
    list_filter = ("status", "product_import", "created_at")
    search_fields = ("category", "product_import__id")
    readonly_fields = ("created_at",)
    list_select_related = ("product_import",)
    actions = [
        "mark_attr_mapped",
        "mark_translated",
        "mark_keywords_fetched",
        "mark_failed",
        "parse_batch_imports",
        "map_batch_imports",
        "export_batch_imports_xlsx",
        "export_batch_imports_csv",
    ]

    @admin.action(description="Mark selected batches as attr_mapped")
    def mark_attr_mapped(self, request, queryset):
        queryset.update(status=CategoryBatch.Status.ATTR_MAPPED)

    @admin.action(description="Mark selected batches as translated")
    def mark_translated(self, request, queryset):
        queryset.update(status=CategoryBatch.Status.TRANSLATED)

    @admin.action(description="Mark selected batches as keywords_fetched")
    def mark_keywords_fetched(self, request, queryset):
        queryset.update(status=CategoryBatch.Status.KEYWORDS_FETCHED)

    @admin.action(description="Mark selected batches as failed")
    def mark_failed(self, request, queryset):
        queryset.update(status=CategoryBatch.Status.FAILED)

    @admin.action(description="Parse imports for selected batches")
    def parse_batch_imports(self, request, queryset):
        for batch in queryset.select_related("product_import"):
            _run_cmd(request, f"Parse import {batch.product_import_id}", "import_parse", import_id=batch.product_import_id)

    @admin.action(description="Map imports for selected batches")
    def map_batch_imports(self, request, queryset):
        for batch in queryset.select_related("product_import"):
            _run_cmd(request, f"Map import {batch.product_import_id}", "import_map", import_id=batch.product_import_id)

    @admin.action(description="Export imports for selected batches (XLSX)")
    def export_batch_imports_xlsx(self, request, queryset):
        for batch in queryset.select_related("product_import"):
            _run_cmd(
                request,
                f"Export import {batch.product_import_id}",
                "import_export",
                import_id=batch.product_import_id,
                format="xlsx",
            )

    @admin.action(description="Export imports for selected batches (CSV)")
    def export_batch_imports_csv(self, request, queryset):
        for batch in queryset.select_related("product_import"):
            _run_cmd(
                request,
                f"Export import {batch.product_import_id}",
                "import_export",
                import_id=batch.product_import_id,
                format="csv",
            )


@admin.register(ImportColumnMapping)
class ImportColumnMappingAdmin(admin.ModelAdmin):
    list_display = ("category_batch", "source_attr_name", "strategy", "target_attribute", "confidence")
    list_filter = ("strategy", "category_batch")
    search_fields = ("source_attr_name", "target_attribute__code", "category_batch__category")
    autocomplete_fields = ("category_batch", "target_attribute")
