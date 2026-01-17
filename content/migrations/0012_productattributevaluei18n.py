import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0011_producttype_main_category"),
        ("content", "0011_producttypei18n_main_category"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductAttributeValueI18n",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("value_text", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "locale",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="product_attribute_value_translations",
                        to="content.locale",
                    ),
                ),
                (
                    "product_attribute_value",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="i18n",
                        to="catalog.productattributevalue",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("product_attribute_value", "locale"),
                        name="uniq_pav_locale",
                    )
                ],
                "indexes": [
                    models.Index(fields=["locale"], name="idx_pav_i18n_locale"),
                ],
            },
        ),
    ]
