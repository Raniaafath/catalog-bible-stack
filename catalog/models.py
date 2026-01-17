import uuid

from django.db import models


class ProductType(models.Model):
    code = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    default_label = models.CharField(max_length=200, blank=True)
    main_category = models.CharField(max_length=200, blank=True, default="")
    category_path = models.TextField(blank=True, default="")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return self.code


class Product(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        DISCONTINUED = "discontinued", "Discontinued"

    product_type = models.ForeignKey(
        ProductType,
        on_delete=models.PROTECT,
        related_name="products",
    )
    code = models.CharField(max_length=150, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    series = models.CharField(max_length=255, null=True, blank=True)
    default_label = models.CharField(max_length=200, blank=True)
    brand = models.CharField(max_length=255, null=True, blank=True)
    model = models.CharField(max_length=255, null=True, blank=True)
    source_title = models.TextField(blank=True, default="")
    source_description = models.TextField(blank=True, default="")
    source_locale = models.CharField(max_length=15, blank=True, default="")
    source_supplier = models.CharField(max_length=100, blank=True, default="")
    source_sku = models.CharField(max_length=150, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        if self.code:
            return self.code
        parts = [p for p in (self.brand, self.model) if p]
        return " ".join(parts) if parts else f"Product {self.pk}"


class Variant(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants",
    )
    barcode = models.CharField(max_length=32, null=True, blank=True, db_index=True)
    mpn = models.CharField(max_length=64, null=True, blank=True)
    internal_sku = models.TextField(default=uuid.uuid4, unique=True)
    sku = models.CharField(max_length=100, unique=True, null=True, blank=True)
    axis_signature = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["product"], name="idx_variant_product"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["barcode"],
                condition=models.Q(barcode__isnull=False) & ~models.Q(barcode=""),
                name="uniq_variant_barcode",
            ),
            models.UniqueConstraint(
                fields=["product", "axis_signature"],
                condition=models.Q(axis_signature__isnull=False),
                name="uniq_variant_product_axis_signature_when_set",
            ),
        ]

    def __str__(self) -> str:
        return self.sku or f"Variant {self.pk}"


class Attribute(models.Model):
    class DataType(models.TextChoices):
        TEXT = "text", "Text"
        NUMBER = "number", "Number"
        BOOL = "bool", "Boolean"
        ENUM = "enum", "Enum"
        JSON = "json", "JSON"

    code = models.SlugField(unique=True)
    data_type = models.CharField(max_length=20, choices=DataType.choices)
    unit = models.CharField(max_length=50, null=True, blank=True)
    is_multi = models.BooleanField(default=False)
    is_value_translatable = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return self.code


class AttributeValue(models.Model):
    attribute = models.ForeignKey(
        Attribute,
        on_delete=models.CASCADE,
        related_name="values",
    )
    code = models.SlugField()
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["attribute_id", "sort_order", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["attribute", "code"],
                name="uniq_attribute_value_code",
            )
        ]

    def __str__(self) -> str:
        return f"{self.attribute}:{self.code}"


class ProductTypeAttribute(models.Model):
    product_type = models.ForeignKey(
        ProductType,
        on_delete=models.CASCADE,
        related_name="attributes",
    )
    attribute = models.ForeignKey(
        Attribute,
        on_delete=models.PROTECT,
        related_name="product_types",
    )
    required = models.BooleanField(default=False)
    filterable = models.BooleanField(default=False)
    variant_level = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product_type", "attribute"],
                name="uniq_product_type_attribute",
            )
        ]

    def __str__(self) -> str:
        return f"{self.product_type} - {self.attribute}"


class ProductAttributeValue(models.Model):
    product = models.ForeignKey(
        Product,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="attribute_values",
    )
    variant = models.ForeignKey(
        Variant,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="attribute_values",
    )
    attribute = models.ForeignKey(
        Attribute,
        on_delete=models.PROTECT,
        related_name="attribute_values",
    )
    attribute_value = models.ForeignKey(
        AttributeValue,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="attribute_values",
    )
    value_text = models.TextField(null=True, blank=True)
    value_number = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    value_bool = models.BooleanField(null=True, blank=True)
    value_json = models.JSONField(null=True, blank=True)
    unit = models.CharField(max_length=50, null=True, blank=True)
    is_axis = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(product__isnull=False, variant__isnull=True)
                | models.Q(product__isnull=True, variant__isnull=False),
                name="chk_attribute_value_scope",
            ),
            models.CheckConstraint(
                condition=models.Q(attribute_value__isnull=False)
                | models.Q(value_text__isnull=False)
                | models.Q(value_number__isnull=False)
                | models.Q(value_bool__isnull=False)
                | models.Q(value_json__isnull=False),
                name="chk_attribute_value_present",
            ),
            models.UniqueConstraint(
                fields=["product", "attribute"],
                condition=models.Q(product__isnull=False),
                name="uniq_product_attribute_value",
            ),
            models.UniqueConstraint(
                fields=["variant", "attribute"],
                condition=models.Q(variant__isnull=False),
                name="uniq_variant_attribute_value",
            ),
        ]
        indexes = [
            models.Index(fields=["attribute"], name="idx_pav_attribute"),
            models.Index(fields=["attribute", "attribute_value"], name="idx_pav_attr_value"),
        ]

    def __str__(self) -> str:
        target = self.product or self.variant
        return f"{target} - {self.attribute}"


class ProductVariantAxis(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variant_axes",
    )
    attribute = models.ForeignKey(
        Attribute,
        on_delete=models.PROTECT,
        related_name="variant_axes",
    )
    position = models.IntegerField(default=0)
    label_override = models.TextField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "attribute"],
                name="uniq_product_variant_axis",
            )
        ]
        indexes = [
            models.Index(fields=["product", "position"], name="idx_product_axis_position"),
        ]

    def __str__(self) -> str:
        return f"{self.product} - {self.attribute}"


class BundleComponent(models.Model):
    bundle_variant = models.ForeignKey(
        Variant,
        on_delete=models.CASCADE,
        related_name="bundle_components",
    )
    component_variant = models.ForeignKey(
        Variant,
        on_delete=models.PROTECT,
        related_name="component_of_bundles",
    )
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["bundle_variant", "component_variant"],
                name="uniq_bundle_component",
            ),
            models.CheckConstraint(
                condition=~models.Q(bundle_variant=models.F("component_variant")),
                name="chk_bundle_component_not_self",
            ),
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name="chk_bundle_component_quantity_gt_0",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.bundle_variant} includes {self.component_variant} x {self.quantity}"
