# Generated manually on 2026-01-17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('importer', '0016_add_group_by_product_key_setting'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productimport',
            name='group_by_product_key',
            field=models.BooleanField(
                default=False,
                help_text=(
                    "If True, variants with the same PRODUCT_KEY will be grouped into one Product. "
                    "If False, each variant will get its own Product (standalone mode) for manual grouping later. "
                    "PRODUCT_KEY column will still be parsed but won't be used for grouping."
                )
            ),
        ),
    ]
