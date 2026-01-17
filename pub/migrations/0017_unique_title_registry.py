from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("pub", "0016_generation_output_approval"),
    ]

    operations = [
        migrations.CreateModel(
            name="UniqueTitle",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "scope",
                    models.CharField(
                        choices=[("parent", "Parent"), ("variant", "Variant")],
                        max_length=20,
                    ),
                ),
                ("normalized_title", models.TextField()),
                ("raw_title", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "channel",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="unique_titles",
                        to="pub.channel",
                    ),
                ),
                (
                    "locale",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="unique_titles",
                        to="content.locale",
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="unique_titles",
                        to="catalog.product",
                    ),
                ),
                (
                    "product_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="unique_titles",
                        to="catalog.producttype",
                    ),
                ),
                (
                    "variant",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="unique_titles",
                        to="catalog.variant",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(product__isnull=False, variant__isnull=True)
                        | models.Q(product__isnull=True, variant__isnull=False),
                        name="chk_unique_title_scope",
                    ),
                    models.UniqueConstraint(
                        fields=("product_type", "locale", "channel", "scope", "normalized_title"),
                        name="uniq_unique_title_scope_norm",
                    ),
                ],
                "indexes": [
                    models.Index(fields=["product_type", "locale", "channel"], name="idx_unique_title_scope"),
                    models.Index(fields=["normalized_title"], name="idx_unique_title_norm"),
                ],
            },
        ),
    ]
