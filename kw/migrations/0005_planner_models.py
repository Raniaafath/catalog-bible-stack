import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0003_producttype_i18n"),
        ("pub", "0004_channel_policies"),
        ("kw", "0004_candidate_drop_channel_code"),
    ]

    operations = [
        migrations.CreateModel(
            name="PlannerRun",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("geo_target", models.CharField(blank=True, max_length=100, null=True)),
                ("request_json", models.JSONField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("queued", "Queued"),
                            ("running", "Running"),
                            ("success", "Success"),
                            ("failed", "Failed"),
                        ],
                        default="queued",
                        max_length=20,
                    ),
                ),
                ("error_json", models.JSONField(blank=True, null=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "channel",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="planner_runs",
                        to="pub.channel",
                    ),
                ),
                (
                    "locale",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="planner_runs",
                        to="content.locale",
                    ),
                ),
                (
                    "source",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="planner_runs",
                        to="kw.source",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="PlannerSeed",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("term", models.TextField()),
                ("normalized_term", models.TextField()),
                (
                    "seed_type",
                    models.CharField(
                        choices=[
                            ("head", "Head"),
                            ("feature", "Feature"),
                            ("brand", "Brand"),
                            ("competitor", "Competitor"),
                            ("category", "Category"),
                        ],
                        max_length=20,
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "locale",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="planner_seeds",
                        to="content.locale",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["locale", "is_active"], name="idx_planner_seed_locale_active")
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("locale", "normalized_term"), name="uniq_planner_seed_locale_normalized"
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="PlannerRunKeyword",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("raw_json", models.JSONField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "keyword",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="planner_runs",
                        to="kw.keyword",
                    ),
                ),
                (
                    "run",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="run_keywords",
                        to="kw.plannerrun",
                    ),
                ),
                (
                    "seed",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="run_keywords",
                        to="kw.plannerseed",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["keyword"], name="idx_planner_run_keyword_keyword"),
                    models.Index(fields=["run"], name="idx_planner_run_keyword_run"),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("run", "keyword"), name="uniq_planner_run_keyword"
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="PlannerRunSeed",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "run",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="run_seeds",
                        to="kw.plannerrun",
                    ),
                ),
                (
                    "seed",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="run_seeds",
                        to="kw.plannerseed",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("run", "seed"), name="uniq_planner_run_seed")
                ],
            },
        ),
        migrations.AddField(
            model_name="metric",
            name="planner_run",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="metrics",
                to="kw.plannerrun",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="metric",
            name="uniq_metric_keyword_source_month",
        ),
        migrations.AddConstraint(
            model_name="metric",
            constraint=models.UniqueConstraint(
                fields=("keyword", "source", "month", "planner_run"),
                name="uniq_metric_keyword_source_month_run",
            ),
        ),
    ]
