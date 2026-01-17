from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kw", "0006_shorten_planner_run_keyword_indexes"),
    ]

    operations = [
        migrations.AddField(
            model_name="attributemap",
            name="reason",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="attributemap",
            name="status",
            field=models.CharField(
                choices=[("suggested", "Suggested"), ("approved", "Approved"), ("rejected", "Rejected")],
                default="suggested",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="attributemap",
            name="tagged_by",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name="attributemap",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
    ]
