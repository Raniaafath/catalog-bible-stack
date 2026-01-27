from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0015_add_channel_to_translation_task"),
    ]

    operations = [
        migrations.AddField(
            model_name="translationtask",
            name="items_total",
            field=models.IntegerField(default=0, help_text="Total items to translate"),
        ),
        migrations.AddField(
            model_name="translationtask",
            name="items_completed",
            field=models.IntegerField(default=0, help_text="Items translated so far"),
        ),
        migrations.AddField(
            model_name="translationtask",
            name="started_at",
            field=models.DateTimeField(blank=True, null=True, help_text="When processing started"),
        ),
        migrations.AddField(
            model_name="translationtask",
            name="finished_at",
            field=models.DateTimeField(blank=True, null=True, help_text="When processing finished"),
        ),
    ]
