import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Attribute",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.SlugField(unique=True)),
                (
                    "data_type",
                    models.CharField(
                        choices=[
                            ("text", "Text"),
                            ("number", "Number"),
                            ("bool", "Boolean"),
                            ("enum", "Enum"),
                            ("json", "JSON"),
                        ],
                        max_length=20,
                    ),
                ),
                ("unit", models.CharField(blank=True, max_length=50, null=True)),
                ("is_multi", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["code"]},
        ),
        migrations.CreateModel(
            name="ProductType",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.SlugField(unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["code"]},
        ),
        migrations.CreateModel(
            name="Product",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("brand", models.CharField(blank=True, max_length=255, null=True)),
                ("model", models.CharField(blank=True, max_length=255, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "product_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="products",
                        to="catalog.producttype",
                    ),
                ),
            ],
            options={},
        ),
        migrations.CreateModel(
            name="Variant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sku", models.CharField(blank=True, max_length=100, null=True, unique=True)),
                ("axis_signature", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="variants",
                        to="catalog.product",
                    ),
                ),
            ],
            options={
                "indexes": [models.Index(fields=["product"], name="idx_variant_product")],
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(("axis_signature__isnull", False)),
                        fields=("product", "axis_signature"),
                        name="uniq_variant_product_axis_signature_when_set",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="AttributeValue",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.SlugField()),
                ("sort_order", models.IntegerField(default=0)),
                (
                    "attribute",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="values",
                        to="catalog.attribute",
                    ),
                ),
            ],
            options={
                "ordering": ["attribute_id", "sort_order", "code"],
                "constraints": [
                    models.UniqueConstraint(fields=("attribute", "code"), name="uniq_attribute_value_code")
                ],
            },
        ),
        migrations.CreateModel(
            name="ProductTypeAttribute",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("required", models.BooleanField(default=False)),
                ("filterable", models.BooleanField(default=False)),
                ("variant_level", models.BooleanField(default=False)),
                (
                    "attribute",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="product_types",
                        to="catalog.attribute",
                    ),
                ),
                (
                    "product_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attributes",
                        to="catalog.producttype",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("product_type", "attribute"), name="uniq_product_type_attribute")
                ]
            },
        ),
        migrations.CreateModel(
            name="ProductAttributeValue",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("value_text", models.TextField(blank=True, null=True)),
                ("value_number", models.DecimalField(blank=True, decimal_places=6, max_digits=18, null=True)),
                ("value_bool", models.BooleanField(blank=True, null=True)),
                ("value_json", models.JSONField(blank=True, null=True)),
                ("unit", models.CharField(blank=True, max_length=50, null=True)),
                (
                    "attribute",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="attribute_values",
                        to="catalog.attribute",
                    ),
                ),
                (
                    "attribute_value",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="attribute_values",
                        to="catalog.attributevalue",
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attribute_values",
                        to="catalog.product",
                    ),
                ),
                (
                    "variant",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attribute_values",
                        to="catalog.variant",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ProductVariantAxis",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("position", models.IntegerField(default=0)),
                ("label_override", models.TextField(blank=True, null=True)),
                (
                    "attribute",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="variant_axes",
                        to="catalog.attribute",
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="variant_axes",
                        to="catalog.product",
                    ),
                ),
            ],
            options={
                "indexes": [models.Index(fields=["product", "position"], name="idx_product_axis_position")],
                "constraints": [
                    models.UniqueConstraint(fields=("product", "attribute"), name="uniq_product_variant_axis")
                ],
            },
        ),
        migrations.CreateModel(
            name="BundleComponent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.PositiveIntegerField(default=1)),
                (
                    "bundle_variant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bundle_components",
                        to="catalog.variant",
                    ),
                ),
                (
                    "component_variant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="component_of_bundles",
                        to="catalog.variant",
                    ),
                ),
            ],
            options={},
        ),
        migrations.AddConstraint(
            model_name="productattributevalue",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(("product__isnull", False), ("variant__isnull", True), _connector="AND"),
                    models.Q(("product__isnull", True), ("variant__isnull", False), _connector="AND"),
                    _connector="OR",
                ),
                name="chk_attribute_value_scope",
            ),
        ),
        migrations.AddConstraint(
            model_name="productattributevalue",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("attribute_value__isnull", False),
                    ("value_text__isnull", False),
                    ("value_number__isnull", False),
                    ("value_bool__isnull", False),
                    ("value_json__isnull", False),
                    _connector="OR",
                ),
                name="chk_attribute_value_present",
            ),
        ),
        migrations.AddConstraint(
            model_name="productattributevalue",
            constraint=models.UniqueConstraint(
                condition=models.Q(("product__isnull", False)),
                fields=("product", "attribute"),
                name="uniq_product_attribute_value",
            ),
        ),
        migrations.AddConstraint(
            model_name="productattributevalue",
            constraint=models.UniqueConstraint(
                condition=models.Q(("variant__isnull", False)),
                fields=("variant", "attribute"),
                name="uniq_variant_attribute_value",
            ),
        ),
        migrations.AddConstraint(
            model_name="bundlecomponent",
            constraint=models.UniqueConstraint(
                fields=("bundle_variant", "component_variant"),
                name="uniq_bundle_component",
            ),
        ),
        migrations.AddConstraint(
            model_name="bundlecomponent",
            constraint=models.CheckConstraint(
                condition=~models.Q(("bundle_variant", models.F("component_variant"))),
                name="chk_bundle_component_not_self",
            ),
        ),
        migrations.AddConstraint(
            model_name="bundlecomponent",
            constraint=models.CheckConstraint(
                condition=models.Q(("quantity__gt", 0)), name="chk_bundle_component_quantity_gt_0"
            ),
        ),
    ]
