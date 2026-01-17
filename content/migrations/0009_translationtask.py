from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0008_drop_productmedia_unique_url"),
    ]

    operations = [
        migrations.CreateModel(
            name="TranslationTask",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("locale", models.CharField(max_length=15)),
                ("scope", models.CharField(max_length=30)),
                ("target_ids", models.JSONField(default=list)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("in_progress", "In Progress"),
                            ("done", "Done"),
                            ("failed", "Failed"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("error", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "indexes": [
                    models.Index(fields=["locale", "scope", "status"], name="idx_trtask_scope_status"),
                ],
            },
        ),
    ]
