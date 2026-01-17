import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("catalog", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Locale",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=15, unique=True)),
                ("name", models.CharField(blank=True, max_length=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["code"]},
        ),
        migrations.CreateModel(
            name="ProductMedia",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("image", "Image"), ("pdf", "PDF"), ("video", "Video"), ("tech_sheet", "Tech Sheet"), ("other", "Other")], max_length=20)),
                ("url", models.URLField(max_length=1000)),
                ("sort_order", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="media", to="catalog.product")),
            ],
            options={"ordering": ["product_id", "sort_order", "id"]},
        ),
        migrations.CreateModel(
            name="ProductI18n",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(blank=True, max_length=255)),
                ("description", models.TextField(blank=True)),
                ("meta_title", models.CharField(blank=True, max_length=255)),
                ("meta_description", models.TextField(blank=True)),
                ("slug", models.SlugField(blank=True, max_length=255)),
                ("locale", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="product_translations", to="content.locale")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="i18n", to="catalog.product")),
            ],
        ),
        migrations.CreateModel(
            name="ContentBlock",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("block_type", models.CharField(max_length=50)),
                ("body", models.TextField()),
                ("sort_order", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("locale", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="content_blocks", to="content.locale")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="content_blocks", to="catalog.product")),
            ],
            options={
                "indexes": [
                    models.Index(fields=["product", "locale", "sort_order"], name="idx_block_product_locale_sort")
                ]
            },
        ),
        migrations.CreateModel(
            name="ComplianceClaim",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=80)),
                ("value", models.CharField(blank=True, max_length=255)),
                ("document_url", models.URLField(blank=True, max_length=1000)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="compliance_claims", to="catalog.product")),
            ],
        ),
        migrations.CreateModel(
            name="AttributeI18n",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label", models.CharField(max_length=255)),
                ("attribute", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="i18n", to="catalog.attribute")),
                ("locale", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="attribute_translations", to="content.locale")),
            ],
        ),
        migrations.CreateModel(
            name="AttributeValueI18n",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label", models.CharField(max_length=255)),
                ("attribute_value", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="i18n", to="catalog.attributevalue")),
                ("locale", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="attribute_value_translations", to="content.locale")),
            ],
        ),
        migrations.AddConstraint(
            model_name="producti18n",
            constraint=models.UniqueConstraint(fields=("product", "locale"), name="uniq_product_locale"),
        ),
        migrations.AddConstraint(
            model_name="producti18n",
            constraint=models.UniqueConstraint(
                condition=models.Q(("slug__isnull", False), ("slug", ""), _connector="AND", _negated=True),
                fields=("locale", "slug"),
                name="uniq_locale_slug_when_set",
            ),
        ),
        migrations.AddConstraint(
            model_name="attributei18n",
            constraint=models.UniqueConstraint(fields=("attribute", "locale"), name="uniq_attribute_locale"),
        ),
        migrations.AddConstraint(
            model_name="attributevaluei18n",
            constraint=models.UniqueConstraint(fields=("attribute_value", "locale"), name="uniq_attribute_value_locale"),
        ),
        migrations.AddConstraint(
            model_name="complianceclaim",
            constraint=models.UniqueConstraint(fields=("product", "code"), name="uniq_product_compliance_code"),
        ),
    ]
