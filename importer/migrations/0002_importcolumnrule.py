from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("importer", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ImportColumnRule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("column_name", models.CharField(max_length=255)),
                ("position", models.PositiveIntegerField(default=0)),
                ("role", models.CharField(choices=[
                    ("PRODUCT_KEY", "Product key (parent)"),
                    ("VARIANT_KEY", "Variant key (SKU)"),
                    ("CATEGORY", "Category"),
                    ("BRAND", "Brand"),
                    ("TITLE", "Title"),
                    ("DESCRIPTION", "Description"),
                    ("ATTRIBUTE", "Attribute"),
                    ("IGNORE", "Ignore"),
                ], default="ATTRIBUTE", max_length=32)),
                ("target_attribute_code", models.CharField(blank=True, default="", max_length=255)),
                ("create_attribute_name", models.CharField(blank=True, default="", max_length=255)),
                ("attribute_type", models.CharField(blank=True, default="", max_length=32)),
                ("unit", models.CharField(blank=True, default="", max_length=32)),
                ("required", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("product_import", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="column_rules", to="importer.productimport")),
            ],
            options={
                "indexes": [
                    models.Index(fields=["product_import", "role"], name="idx_import_column_role"),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="importcolumnrule",
            constraint=models.UniqueConstraint(
                fields=["product_import", "column_name"],
                name="uniq_import_column_rule_per_column",
            ),
        ),
        migrations.AddConstraint(
            model_name="importcolumnrule",
            constraint=models.CheckConstraint(
                condition=Q(
                    ("role", "ATTRIBUTE"),
                )
                | (
                    Q(("target_attribute_code", ""))
                    & Q(("create_attribute_name", ""))
                    & Q(("attribute_type", ""))
                    & Q(("unit", ""))
                ),
                name="chk_non_attribute_fields_empty",
            ),
        ),
    ]
