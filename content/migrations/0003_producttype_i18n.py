import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0003_producttype_structure"),
        ("content", "0002_remove_producti18n_uniq_locale_slug_when_set_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductTypeI18n",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                (
                    "locale",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="product_type_translations",
                        to="content.locale",
                    ),
                ),
                (
                    "product_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="i18n",
                        to="catalog.producttype",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("product_type", "locale"), name="uniq_product_type_locale")
                ]
            },
        ),
    ]
