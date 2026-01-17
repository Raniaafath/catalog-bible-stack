import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0001_initial"),
        ("content", "0001_initial"),
        ("pub", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Template",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("title", "Title"), ("bullets", "Bullets"), ("description", "Description"), ("meta_title", "Meta Title"), ("meta_description", "Meta Description")], max_length=50)),
                ("version", models.IntegerField(default=1)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("active", "Active"), ("archived", "Archived")], default="draft", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("channel", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="templates", to="pub.channel")),
                ("locale", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="templates", to="content.locale")),
                ("product_type", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="templates", to="catalog.producttype")),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("product_type", "locale", "channel", "kind", "version"), name="uniq_template_scope")
                ]
            },
        ),
        migrations.CreateModel(
            name="TemplatePart",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("position", models.IntegerField()),
                ("part_type", models.CharField(choices=[("keyword", "Keyword"), ("axis_attribute", "Axis Attribute"), ("attribute", "Attribute"), ("literal", "Literal"), ("brand", "Brand")], max_length=20)),
                ("keyword_role", models.CharField(blank=True, choices=[("head", "Head"), ("hook", "Hook"), ("supporting", "Supporting"), ("negative", "Negative")], max_length=20, null=True)),
                ("literal_text", models.TextField(blank=True, null=True)),
                ("required", models.BooleanField(default=False)),
                ("fallback_text", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("attribute", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="template_parts", to="catalog.attribute")),
                ("template", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="parts", to="pub.template")),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("template", "position"), name="uniq_template_part_position"),
                    models.CheckConstraint(
                        condition=(
                            models.Q(("part_type", "literal"))
                            & models.Q(("literal_text__isnull", False))
                            & ~models.Q(("literal_text", ""))
                        )
                        | ~models.Q(("part_type", "literal")),
                        name="chk_part_literal_requires_text",
                    ),
                    models.CheckConstraint(
                        condition=(
                            models.Q(("part_type__in", ["attribute", "axis_attribute"]))
                            & models.Q(("attribute__isnull", False))
                        )
                        | ~models.Q(("part_type__in", ["attribute", "axis_attribute"])),
                        name="chk_part_attribute_requires_attr",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("part_type", "keyword")) & models.Q(("keyword_role__isnull", False))
                        | ~models.Q(("part_type", "keyword")),
                        name="chk_part_keyword_requires_role",
                    ),
                ]
            },
        ),
    ]
