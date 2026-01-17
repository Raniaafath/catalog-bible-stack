from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0011_producttype_main_category"),
    ]

    operations = [
        migrations.AddField(
            model_name="attribute",
            name="is_value_translatable",
            field=models.BooleanField(default=False),
        ),
    ]
