from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0016_add_translation_task_progress_fields"),
        ("catalog", "0018_remove_product_source_description_and_more"),
        ("pub", "0022_remove_channellocalepolicy_uniq_channel_locale_policy_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductHookTerm",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("term", models.CharField(max_length=255)),
                ("priority", models.IntegerField(db_index=True, default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "channel",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="product_hook_terms",
                        to="pub.channel",
                    ),
                ),
                (
                    "locale",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="product_hook_terms",
                        to="content.locale",
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="hook_terms",
                        to="catalog.product",
                    ),
                ),
            ],
            options={
                "ordering": ["-priority", "id"],
            },
        ),
        migrations.AddIndex(
            model_name="producthookterm",
            index=models.Index(
                fields=["product", "locale", "channel"],
                name="idx_producthookterm_lookup",
            ),
        ),
        migrations.AddConstraint(
            model_name="producthookterm",
            constraint=models.UniqueConstraint(
                condition=models.Q(("channel__isnull", True)),
                fields=("product", "locale", "term"),
                name="uq_producthookterm_product_locale_term_channel_null",
            ),
        ),
        migrations.AddConstraint(
            model_name="producthookterm",
            constraint=models.UniqueConstraint(
                condition=models.Q(("channel__isnull", False)),
                fields=("product", "locale", "channel", "term"),
                name="uq_producthookterm_product_locale_channel_term",
            ),
        ),
    ]
