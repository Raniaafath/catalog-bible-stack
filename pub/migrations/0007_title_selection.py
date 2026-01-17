from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("pub", "0006_generation_output_head_hook"),
        ("kw", "0014_product_keyword_map_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="TitleSelection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("draft", "Draft"), ("approved", "Approved"), ("archived", "Archived")], default="draft", max_length=16)),
                ("head_text", models.CharField(max_length=255)),
                ("head_source", models.CharField(max_length=64)),
                ("head_keyword_id", models.IntegerField(blank=True, null=True)),
                ("hook_text", models.CharField(blank=True, default="", max_length=255)),
                ("hook_source", models.CharField(blank=True, default="", max_length=64)),
                ("hook_keyword_id", models.IntegerField(blank=True, null=True)),
                ("overrides_json", models.JSONField(blank=True, default=dict)),
                ("meta_json", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("channel", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="pub.channel")),
                ("locale", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="content.locale")),
                ("planner_run", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="kw.plannerrun")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="catalog.product")),
                ("variant", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="catalog.variant")),
            ],
            options={
                "indexes": [
                    models.Index(fields=["product", "locale", "channel"], name="pub_titlese_product_8020a2_idx"),
                    models.Index(fields=["planner_run"], name="pub_titlese_planner_dba44b_idx"),
                    models.Index(fields=["status"], name="pub_titlese_status_b7b7b7_idx"),
                ],
                "constraints": [
                    models.UniqueConstraint(fields=("product", "variant", "locale", "channel"), name="uniq_title_selection_scope")
                ],
            },
        ),
        migrations.AddField(
            model_name="generationoutput",
            name="selection",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="generation_outputs", to="pub.titleselection"),
        ),
    ]
