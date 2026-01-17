from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pub", "0014_content_sets_batches"),
    ]

    operations = [
        migrations.CreateModel(
            name="ExportProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200)),
                ("context", models.CharField(default="content", max_length=64)),
                ("format", models.CharField(choices=[("csv", "CSV"), ("xlsx", "XLSX")], default="csv", max_length=8)),
                ("version", models.IntegerField(default=1)),
                ("columns_json", models.JSONField(default=list)),
                ("options_json", models.JSONField(blank=True, default=dict)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("channel", models.ForeignKey(on_delete=models.PROTECT, to="pub.channel")),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("channel", "context", "format", "version"),
                        name="uniq_export_profile_version",
                    )
                ],
                "indexes": [
                    models.Index(
                        fields=["channel", "context", "is_active"],
                        name="idx_export_profile_active",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="ExportJob",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
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
                ("result_file", models.CharField(blank=True, default="", max_length=255)),
                ("stats_json", models.JSONField(blank=True, default=dict)),
                ("error_message", models.TextField(blank=True, default="")),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("batch", models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, to="pub.generationbatch")),
                ("profile", models.ForeignKey(on_delete=models.PROTECT, to="pub.exportprofile")),
            ],
            options={
                "indexes": [
                    models.Index(fields=["status"], name="idx_export_job_status"),
                ],
            },
        ),
    ]
