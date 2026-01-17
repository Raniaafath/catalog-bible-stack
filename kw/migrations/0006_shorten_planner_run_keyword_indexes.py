from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kw", "0005_planner_models"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="plannerrunkeyword",
            name="idx_planner_run_keyword_keyword",
        ),
        migrations.RemoveIndex(
            model_name="plannerrunkeyword",
            name="idx_planner_run_keyword_run",
        ),
        migrations.AddIndex(
            model_name="plannerrunkeyword",
            index=models.Index(fields=["keyword"], name="idx_prk_keyword"),
        ),
        migrations.AddIndex(
            model_name="plannerrunkeyword",
            index=models.Index(fields=["run"], name="idx_prk_run"),
        ),
    ]
