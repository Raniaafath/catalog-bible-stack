from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pub", "0015_export_profiles_jobs"),
    ]

    operations = [
        migrations.AddField(
            model_name="generationoutput",
            name="is_approved",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="generationoutput",
            name="approved_by",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="generationoutput",
            name="approved_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
