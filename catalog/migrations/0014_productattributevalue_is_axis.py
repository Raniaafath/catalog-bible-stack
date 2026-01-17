from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0013_set_translatable_for_text_attrs"),
    ]

    operations = [
        migrations.AddField(
            model_name="productattributevalue",
            name="is_axis",
            field=models.BooleanField(default=False),
        ),
    ]
