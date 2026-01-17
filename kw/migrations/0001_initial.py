import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("content", "0001_initial"),
        ("catalog", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Concept",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=100, unique=True)),
                ("concept_type", models.CharField(choices=[("head_term", "Head Term"), ("feature", "Feature"), ("intent", "Intent"), ("negative", "Negative"), ("brand", "Brand"), ("size", "Size"), ("other", "Other")], max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="Keyword",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("term", models.TextField()),
                ("normalized_term", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("locale", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="keywords", to="content.locale")),
            ],
            options={
                "indexes": [models.Index(fields=["locale", "term"], name="idx_keyword_locale_term")],
                "constraints": [models.UniqueConstraint(fields=("locale", "normalized_term"), name="uniq_keyword_locale_normalized")],
            },
        ),
        migrations.CreateModel(
            name="Source",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=100, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="KeywordConcept",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("confidence", models.DecimalField(blank=True, decimal_places=4, max_digits=5, null=True)),
                ("tagged_by", models.CharField(max_length=50)),
                ("reason", models.TextField(blank=True)),
                ("tagged_at", models.DateTimeField(auto_now_add=True)),
                ("concept", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="keywords", to="kw.concept")),
                ("keyword", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="concepts", to="kw.keyword")),
            ],
            options={
                "constraints": [models.UniqueConstraint(fields=("keyword", "concept"), name="uniq_keyword_concept")],
            },
        ),
        migrations.CreateModel(
            name="ProductTypeMap",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("confidence", models.DecimalField(blank=True, decimal_places=4, max_digits=5, null=True)),
                ("reason", models.TextField(blank=True)),
                ("keyword", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="product_types", to="kw.keyword")),
                ("product_type", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="keyword_maps", to="catalog.producttype")),
            ],
            options={
                "constraints": [models.UniqueConstraint(fields=("keyword", "product_type"), name="uniq_keyword_product_type")],
            },
        ),
        migrations.CreateModel(
            name="Metric",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("month", models.DateField()),
                ("avg_searches", models.IntegerField(blank=True, null=True)),
                ("competition", models.DecimalField(blank=True, decimal_places=4, max_digits=10, null=True)),
                ("cpc", models.DecimalField(blank=True, decimal_places=4, max_digits=10, null=True)),
                ("raw_json", models.JSONField(blank=True, null=True)),
                ("keyword", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="metrics", to="kw.keyword")),
                ("source", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="metrics", to="kw.source")),
            ],
            options={
                "indexes": [models.Index(fields=["month"], name="idx_metric_month")],
                "constraints": [models.UniqueConstraint(fields=("keyword", "source", "month"), name="uniq_metric_keyword_source_month")],
            },
        ),
        migrations.CreateModel(
            name="AttributeMap",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("confidence", models.DecimalField(blank=True, decimal_places=4, max_digits=5, null=True)),
                ("attribute", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="keyword_maps", to="catalog.attribute")),
                ("attribute_value", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="keyword_maps", to="catalog.attributevalue")),
                ("keyword", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attribute_maps", to="kw.keyword")),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(condition=models.Q(("attribute_value__isnull", False)), fields=("keyword", "attribute", "attribute_value"), name="uniq_keyword_attribute_value"),
                    models.UniqueConstraint(condition=models.Q(("attribute_value__isnull", True)), fields=("keyword", "attribute"), name="uniq_keyword_attribute_no_value"),
                ],
            },
        ),
        migrations.CreateModel(
            name="Candidate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("channel_code", models.CharField(blank=True, max_length=50, null=True)),
                ("role", models.CharField(choices=[("head", "Head"), ("hook", "Hook"), ("supporting", "Supporting"), ("negative", "Negative")], max_length=20)),
                ("weight", models.IntegerField(default=0)),
                ("status", models.CharField(choices=[("suggested", "Suggested"), ("approved", "Approved"), ("rejected", "Rejected")], default="suggested", max_length=20)),
                ("selected_by", models.CharField(blank=True, max_length=50)),
                ("reason", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("keyword", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="candidates", to="kw.keyword")),
                ("locale", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="candidates", to="content.locale")),
                ("product", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="candidates", to="catalog.product")),
                ("variant", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="candidates", to="catalog.variant")),
            ],
        ),
        migrations.AddConstraint(
            model_name="candidate",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(("product__isnull", False), ("variant__isnull", True), _connector="AND"),
                    models.Q(("product__isnull", True), ("variant__isnull", False), _connector="AND"),
                    _connector="OR",
                ),
                name="chk_candidate_scope",
            ),
        ),
        migrations.AddConstraint(
            model_name="candidate",
            constraint=models.UniqueConstraint(
                fields=("locale", "channel_code", "keyword", "role", "product", "variant"),
                name="uniq_candidate_scope_keyword_role",
            ),
        ),
    ]
