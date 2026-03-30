# Generated manually for ContentSelection AI description controls

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pub", "0022_remove_channellocalepolicy_uniq_channel_locale_policy_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="contentselection",
            name="description_user_instructions",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="contentselection",
            name="description_ai_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="contentselection",
            name="description_ai_model",
            field=models.CharField(blank=True, default="gpt-4o-mini", max_length=64),
        ),
    ]
