"""Models for product import workflow."""
from django.db import models
from django.db.models import Q

from catalog.models import Attribute


class ProductImport(models.Model):
    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        PARSED = "parsed", "Parsed"
        MAPPED = "mapped", "Mapped"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        COMMITTED = "committed", "Committed"
        FAILED = "failed", "Failed"

    created_by = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    source_file = models.FileField(upload_to="imports/%Y/%m/%d/")
    original_filename = models.CharField(max_length=255, blank=True)
    file_type = models.CharField(max_length=20, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UPLOADED)
    row_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    parse_error_message = models.TextField(
        blank=True,
        help_text="Detailed error message explaining why parsing failed or why 0 rows were detected"
    )
    
    # Import behavior settings
    group_by_product_key = models.BooleanField(
        default=False,
        help_text=(
            "If True, variants with the same PRODUCT_KEY will be grouped into one Product. "
            "If False, each variant will get its own Product (standalone mode) for manual grouping later. "
            "PRODUCT_KEY column will still be parsed but won't be used for grouping."
        )
    )

    def __str__(self) -> str:
        return f"Import {self.id} [{self.status}]"


class ImportColumnMap(models.Model):
    product_import = models.OneToOneField(
        ProductImport,
        on_delete=models.CASCADE,
        related_name="column_map",
    )
    mapping_json = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"ColumnMap {self.product_import_id}"


class ImportRow(models.Model):
    product_import = models.ForeignKey(
        ProductImport,
        on_delete=models.CASCADE,
        related_name="rows",
    )
    row_number = models.IntegerField()
    raw = models.JSONField()
    normalized = models.JSONField(null=True, blank=True)
    errors = models.JSONField(null=True, blank=True)
    is_valid = models.BooleanField(default=True)
    parent_key = models.CharField(max_length=255, blank=True, default='', help_text='Key to group variants under the same parent product')
    is_parent = models.BooleanField(default=False, help_text='Whether this row represents a parent product')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product_import", "row_number"],
                name="uniq_import_row_number",
            )
        ]
        indexes = [
            models.Index(fields=["product_import", "row_number"], name="idx_import_row_number"),
            models.Index(fields=["product_import", "is_valid"], name="idx_import_row_valid"),
            models.Index(fields=["product_import", "parent_key"], name="idx_import_row_parent_key"),
        ]

    def __str__(self) -> str:
        return f"Row {self.row_number} ({self.product_import_id})"


class CategoryBatch(models.Model):
    class Status(models.TextChoices):
        READY = "ready", "Ready"
        ATTR_MAPPED = "attr_mapped", "Attr Mapped"
        TRANSLATED = "translated", "Translated"
        KEYWORDS_FETCHED = "keywords_fetched", "Keywords Fetched"
        FAILED = "failed", "Failed"

    product_import = models.ForeignKey(
        ProductImport,
        on_delete=models.CASCADE,
        related_name="category_batches",
    )
    category = models.CharField(max_length=255)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.READY)
    product_count = models.IntegerField(default=0)
    variant_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Batch {self.id} {self.category} [{self.status}]"


class AttributeMapping(models.Model):
    class Strategy(models.TextChoices):
        MATCHED = "matched", "Matched"
        CREATED = "created", "Created"
        IGNORED = "ignored", "Ignored"

    category_batch = models.ForeignKey(
        CategoryBatch,
        on_delete=models.CASCADE,
        related_name="attribute_mappings",
    )
    source_attr_name = models.CharField(max_length=255)
    target_attribute = models.ForeignKey(
        Attribute,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="import_mappings",
    )
    strategy = models.CharField(max_length=20, choices=Strategy.choices)
    notes = models.TextField(blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["category_batch", "source_attr_name"],
                name="uniq_batch_source_attr",
            )
        ]

    def __str__(self) -> str:
        return f"{self.source_attr_name} ({self.strategy})"


class ImportColumnRule(models.Model):
    class Role(models.TextChoices):
        PRODUCT_KEY = "PRODUCT_KEY", "Product key (parent)"
        VARIANT_KEY = "VARIANT_KEY", "Variant key (SKU)"
        CATEGORY = "CATEGORY", "Category"
        BRAND = "BRAND", "Brand"
        TITLE = "TITLE", "Title"
        DESCRIPTION = "DESCRIPTION", "Description"
        # Variant-level fields
        BARCODE = "BARCODE", "Barcode"
        MPN = "MPN", "MPN (Manufacturer Part Number)"
        SOURCE_SKU = "SOURCE_SKU", "Source SKU"
        SOURCE_SUPPLIER = "SOURCE_SUPPLIER", "Source Supplier"
        SOURCE_LOCALE = "SOURCE_LOCALE", "Source Locale"
        # Product-level fields
        PRODUCT_MODEL = "PRODUCT_MODEL", "Product Model"
        PRODUCT_SERIES = "PRODUCT_SERIES", "Product Series"
        PRODUCT_CODE = "PRODUCT_CODE", "Product Code"
        # Other
        ATTRIBUTE = "ATTRIBUTE", "Attribute"
        IGNORE = "IGNORE", "Ignore"

    product_import = models.ForeignKey(
        ProductImport,
        on_delete=models.CASCADE,
        related_name="column_rules",
    )
    column_name = models.CharField(max_length=255)
    position = models.PositiveIntegerField(default=0)
    role = models.CharField(max_length=32, choices=Role.choices, default=Role.ATTRIBUTE)
    target_attribute_code = models.CharField(max_length=255, blank=True, default="")
    create_attribute_name = models.CharField(max_length=255, blank=True, default="")
    attribute_type = models.CharField(max_length=32, blank=True, default="")
    unit = models.CharField(max_length=32, blank=True, default="")
    required = models.BooleanField(default=False)
    is_variation_axis = models.BooleanField(default=False, help_text="Mark this attribute as a variation axis for generating variants")
    axis_priority = models.IntegerField(default=0, help_text="Priority/position of this variation axis (0-4 for up to 5 axes)")
    variant_level = models.BooleanField(default=False, help_text="Whether this attribute belongs to variant level (not product level)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product_import", "column_name"],
                name="uniq_import_column_rule_per_column",
            ),
            models.CheckConstraint(
                condition=Q(role="ATTRIBUTE")
                | (
                    Q(target_attribute_code="")
                    & Q(create_attribute_name="")
                    & Q(attribute_type="")
                    & Q(unit="")
                ),
                name="chk_non_attribute_fields_empty",
            ),
        ]
        indexes = [
            models.Index(fields=["product_import", "role"], name="idx_import_column_role"),
        ]

    def __str__(self) -> str:
        return f"{self.product_import_id}:{self.column_name} -> {self.role}"
