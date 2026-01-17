from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("catalog", "0014_productattributevalue_is_axis"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductImport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_by", models.CharField(blank=True, max_length=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("source_file", models.FileField(upload_to="imports/%Y/%m/%d/")),
                ("original_filename", models.CharField(blank=True, max_length=255)),
                ("file_type", models.CharField(blank=True, max_length=20)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("uploaded", "Uploaded"),
                            ("parsed", "Parsed"),
                            ("mapped", "Mapped"),
                            ("committed", "Committed"),
                            ("failed", "Failed"),
                        ],
                        default="uploaded",
                        max_length=20,
                    ),
                ),
                ("row_count", models.IntegerField(default=0)),
                ("error_count", models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name="CategoryBatch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("category", models.CharField(max_length=255)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("ready", "Ready"),
                            ("attr_mapped", "Attr Mapped"),
                            ("translated", "Translated"),
                            ("keywords_fetched", "Keywords Fetched"),
                            ("failed", "Failed"),
                        ],
                        default="ready",
                        max_length=30,
                    ),
                ),
                ("product_count", models.IntegerField(default=0)),
                ("variant_count", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "product_import",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="category_batches",
                        to="importer.productimport",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ImportColumnMap",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("mapping_json", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "product_import",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="column_map",
                        to="importer.productimport",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ImportRow",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("row_number", models.IntegerField()),
                ("raw", models.JSONField()),
                ("normalized", models.JSONField(blank=True, null=True)),
                ("errors", models.JSONField(blank=True, null=True)),
                ("is_valid", models.BooleanField(default=True)),
                (
                    "product_import",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="rows",
                        to="importer.productimport",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("product_import", "row_number"),
                        name="uniq_import_row_number",
                    )
                ],
                "indexes": [
                    models.Index(fields=["product_import", "row_number"], name="idx_import_row_number"),
                    models.Index(fields=["product_import", "is_valid"], name="idx_import_row_valid"),
                ],
            },
        ),
        migrations.CreateModel(
            name="AttributeMapping",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_attr_name", models.CharField(max_length=255)),
                (
                    "strategy",
                    models.CharField(
                        choices=[
                            ("matched", "Matched"),
                            ("created", "Created"),
                            ("ignored", "Ignored"),
                        ],
                        max_length=20,
                    ),
                ),
                ("notes", models.TextField(blank=True)),
                ("confidence", models.DecimalField(blank=True, decimal_places=4, max_digits=6, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "category_batch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attribute_mappings",
                        to="importer.categorybatch",
                    ),
                ),
                (
                    "target_attribute",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="import_mappings",
                        to="catalog.attribute",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("category_batch", "source_attr_name"),
                        name="uniq_batch_source_attr",
                    )
                ]
            },
        ),
    ]
