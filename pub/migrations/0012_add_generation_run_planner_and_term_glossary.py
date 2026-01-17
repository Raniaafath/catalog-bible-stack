from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pub", "0011_remove_channellocalepolicy_uniq_channel_locale_policy_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="generationrun",
            name="planner_run",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="generation_runs",
                to="kw.plannerrun",
            ),
        ),
        migrations.CreateModel(
            name="TermGlossary",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("term_norm", models.CharField(max_length=200)),
                ("term", models.CharField(max_length=200)),
                ("short_definition", models.TextField(blank=True)),
                ("synonyms_json", models.JSONField(blank=True, default=list)),
                ("examples_json", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "locale",
                    models.ForeignKey(
                        on_delete=models.PROTECT,
                        related_name="term_glossary",
                        to="content.locale",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("locale", "term_norm"),
                        name="uniq_term_glossary_locale_norm",
                    )
                ],
                "indexes": [
                    models.Index(fields=["locale", "term_norm"], name="idx_term_glossary_locale_norm")
                ],
            },
        ),
    ]
