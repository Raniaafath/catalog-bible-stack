from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pub", "0013_content_generation_outputs"),
    ]

    operations = [
        migrations.CreateModel(
            name="ContentSet",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True, default="")),
                ("context", models.CharField(default="content", max_length=64)),
                ("kind", models.CharField(default="static", max_length=16)),
                ("filter_json", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "channel",
                    models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, to="pub.channel"),
                ),
                (
                    "locale",
                    models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, to="content.locale"),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["channel", "locale"], name="idx_content_set_scope"),
                ],
            },
        ),
        migrations.CreateModel(
            name="ContentSetItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("content_set", models.ForeignKey(on_delete=models.CASCADE, related_name="items", to="pub.contentset")),
                ("product", models.ForeignKey(on_delete=models.CASCADE, to="catalog.product")),
                ("variant", models.ForeignKey(blank=True, null=True, on_delete=models.CASCADE, to="catalog.variant")),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("content_set", "product", "variant"),
                        name="uniq_content_set_member",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="GenerationBatch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("context", models.CharField(default="content", max_length=64)),
                ("mode", models.CharField(default="auto", max_length=16)),
                ("include_descriptions", models.BooleanField(default=False)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("queued", "Queued"),
                            ("running", "Running"),
                            ("done", "Done"),
                            ("failed", "Failed"),
                        ],
                        default="queued",
                        max_length=16,
                    ),
                ),
                ("total", models.IntegerField(default=0)),
                ("generated", models.IntegerField(default=0)),
                ("needs_approval", models.IntegerField(default=0)),
                ("errors", models.IntegerField(default=0)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("content_set", models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, to="pub.contentset")),
                ("channel", models.ForeignKey(on_delete=models.PROTECT, to="pub.channel")),
                ("locale", models.ForeignKey(on_delete=models.PROTECT, to="content.locale")),
                ("planner_run", models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, to="kw.plannerrun")),
            ],
            options={
                "indexes": [
                    models.Index(fields=["status"], name="idx_batch_status"),
                ],
            },
        ),
        migrations.CreateModel(
            name="GenerationBatchItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("generated", "Generated"),
                            ("needs_approval", "Needs Approval"),
                            ("error", "Error"),
                        ],
                        max_length=16,
                    ),
                ),
                ("error_message", models.TextField(blank=True, default="")),
                ("selection_id", models.IntegerField(blank=True, null=True)),
                ("preview_json", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("batch", models.ForeignKey(on_delete=models.CASCADE, related_name="items", to="pub.generationbatch")),
                ("generation_run", models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, to="pub.generationrun")),
                ("product", models.ForeignKey(on_delete=models.CASCADE, to="catalog.product")),
                ("variant", models.ForeignKey(on_delete=models.CASCADE, to="catalog.variant")),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("batch", "variant"),
                        name="uniq_batch_variant",
                    )
                ],
            },
        ),
        migrations.AddField(
            model_name="generationrun",
            name="batch",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="generation_runs",
                to="pub.generationbatch",
            ),
        ),
    ]
