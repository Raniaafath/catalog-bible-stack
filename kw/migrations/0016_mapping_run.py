from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("kw", "0015_alter_productkeywordmap_source"),
        ("importer", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="MappingRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("running", "Running"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("created_by", models.CharField(blank=True, max_length=100)),
                ("algorithm_version", models.CharField(blank=True, max_length=50)),
                ("config_json", models.JSONField(blank=True, default=dict)),
                ("mapping_count", models.IntegerField(default=0)),
                ("product_count", models.IntegerField(default=0)),
                ("keyword_count", models.IntegerField(default=0)),
                ("error_count", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "category_batch",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="mapping_runs",
                        to="importer.categorybatch",
                    ),
                ),
                (
                    "planner_run",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="mapping_runs",
                        to="kw.plannerrun",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["planner_run", "created_at"], name="idx_mapping_run_planner"),
                    models.Index(fields=["status", "created_at"], name="idx_mapping_run_status"),
                ]
            },
        ),
        migrations.AddField(
            model_name="productkeywordmap",
            name="mapping_run",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="product_keyword_maps",
                to="kw.mappingrun",
            ),
        ),
    ]
