from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pub", "0012_add_generation_run_planner_and_term_glossary"),
    ]

    operations = [
        migrations.AddField(
            model_name="generationoutput",
            name="position",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.RunSQL(
            sql="UPDATE pub_generationoutput SET position = 0 WHERE position IS NULL;",
            reverse_sql="UPDATE pub_generationoutput SET position = NULL WHERE position = 0;",
        ),
        migrations.RemoveConstraint(
            model_name="generationoutput",
            name="uniq_generation_output_field",
        ),
        migrations.AddConstraint(
            model_name="generationoutput",
            constraint=models.UniqueConstraint(
                fields=("run", "field", "position"),
                name="uniq_generation_output_field_position",
            ),
        ),
        migrations.CreateModel(
            name="ContentSelection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("context", models.CharField(default="title", max_length=50)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("approved", "Approved"), ("rejected", "Rejected"), ("archived", "Archived")], default="draft", max_length=16)),
                ("created_by_type", models.CharField(choices=[("system", "System"), ("user", "User")], default="system", max_length=10)),
                ("bullets_json", models.JSONField(blank=True, default=list)),
                ("description_text", models.TextField(blank=True)),
                ("meta_json", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("channel", models.ForeignKey(on_delete=models.CASCADE, to="pub.channel")),
                ("locale", models.ForeignKey(on_delete=models.CASCADE, to="content.locale")),
                ("planner_run", models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, to="kw.plannerrun")),
                ("product", models.ForeignKey(on_delete=models.CASCADE, to="catalog.product")),
                ("variant", models.ForeignKey(blank=True, null=True, on_delete=models.CASCADE, to="catalog.variant")),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("product", "variant", "locale", "channel", "context"),
                        name="uniq_content_selection_scope_context",
                    )
                ],
                "indexes": [
                    models.Index(
                        fields=["product", "locale", "channel", "context"],
                        name="idx_cs_scope",
                    ),
                    models.Index(fields=["planner_run"], name="idx_cs_planner_run"),
                    models.Index(fields=["status"], name="idx_cs_status"),
                ],
            },
        ),
        migrations.CreateModel(
            name="ContentEditSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("context", models.CharField(default="title", max_length=50)),
                ("mode", models.CharField(default="review", max_length=10)),
                ("messages_json", models.JSONField(blank=True, default=list)),
                ("meta_json", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("channel", models.ForeignKey(on_delete=models.CASCADE, to="pub.channel")),
                ("content_selection", models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="edit_sessions", to="pub.contentselection")),
                ("locale", models.ForeignKey(on_delete=models.CASCADE, to="content.locale")),
                ("product", models.ForeignKey(on_delete=models.CASCADE, to="catalog.product")),
                ("title_selection", models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="edit_sessions", to="pub.titleselection")),
                ("variant", models.ForeignKey(blank=True, null=True, on_delete=models.CASCADE, to="catalog.variant")),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["product", "locale", "channel", "context"],
                        name="idx_ce_scope",
                    ),
                ],
            },
        ),
    ]
