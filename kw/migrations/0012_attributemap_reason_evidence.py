from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kw", "0011_plannerseed_scope_unique"),
    ]

    operations = [
        migrations.AddField(
            model_name="attributemap",
            name="reason_code",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
        migrations.AddField(
            model_name="attributemap",
            name="evidence",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
