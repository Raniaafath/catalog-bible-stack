import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0001_initial"),
        ("content", "0001_initial"),
        ("pub", "0002_templates"),
    ]

    operations = [
        migrations.CreateModel(
            name="Approval",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("entity_type", models.CharField(max_length=80)),
                ("entity_id", models.BigIntegerField()),
                ("status", models.CharField(choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")], default="pending", max_length=20)),
                ("approved_by", models.CharField(blank=True, max_length=100)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("entity_type", "entity_id"), name="uniq_approval_entity")
                ]
            },
        ),
        migrations.CreateModel(
            name="ChannelListingMap",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("external_id", models.CharField(blank=True, max_length=120)),
                ("last_sync_at", models.DateTimeField(blank=True, null=True)),
                ("sync_status", models.CharField(blank=True, max_length=50)),
                ("error_json", models.JSONField(blank=True, null=True)),
                ("channel", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="variant_listings", to="pub.channel")),
                ("variant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="channel_listings", to="catalog.variant")),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("variant", "channel"), name="uniq_channel_listing_variant_channel")
                ]
            },
        ),
        migrations.CreateModel(
            name="GenerationRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("model_info", models.JSONField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("channel", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="generation_runs", to="pub.channel")),
                ("locale", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="generation_runs", to="content.locale")),
                ("product", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="generation_runs", to="catalog.product")),
                ("template", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="generation_runs", to="pub.template")),
                ("variant", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="generation_runs", to="catalog.variant")),
            ],
            options={
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(("product__isnull", False), ("variant__isnull", True), _connector="AND"),
                            models.Q(("product__isnull", True), ("variant__isnull", False), _connector="AND"),
                            _connector="OR",
                        ),
                        name="chk_generation_run_scope",
                    )
                ]
            },
        ),
        migrations.CreateModel(
            name="GenerationOutput",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("field", models.CharField(max_length=50)),
                ("text", models.TextField()),
                ("score_json", models.JSONField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("run", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="outputs", to="pub.generationrun")),
            ],
            options={
                "constraints": [models.UniqueConstraint(fields=("run", "field"), name="uniq_generation_output_field")]
            },
        ),
    ]
