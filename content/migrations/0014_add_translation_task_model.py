from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0013_lock_fields_for_translations"),
    ]

    operations = [
        migrations.AddField(
            model_name="translationtask",
            name="model",
            field=models.CharField(default="gpt-4o-mini", max_length=50),
        ),
    ]
