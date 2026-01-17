from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0001_initial"),
        ("kw", "0012_attributemap_reason_evidence"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductKeywordMap",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("confidence", models.DecimalField(blank=True, decimal_places=4, max_digits=5, null=True)),
                ("source", models.CharField(choices=[("enum_map", "Enum Map"), ("pav_text", "PAV Text"), ("pav_text_llm", "PAV Text (LLM)")], max_length=20)),
                ("evidence", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("attribute_value", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="product_keyword_maps", to="catalog.attributevalue")),
                ("keyword", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="product_maps", to="kw.keyword")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="keyword_maps", to="catalog.product")),
                ("run", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="product_keyword_maps", to="kw.plannerrun")),
            ],
            options={
                "indexes": [
                    models.Index(fields=["run"], name="idx_pkmap_run"),
                    models.Index(fields=["product"], name="idx_pkmap_product"),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="productkeywordmap",
            constraint=models.UniqueConstraint(fields=("product", "keyword", "run", "source"), name="uniq_product_keyword_run_source"),
        ),
    ]
