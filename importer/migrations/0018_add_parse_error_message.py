# Generated manually on 2026-01-17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('importer', '0017_change_group_by_product_key_default'),
    ]

    operations = [
        migrations.AddField(
            model_name='productimport',
            name='parse_error_message',
            field=models.TextField(
                blank=True,
                help_text="Detailed error message explaining why parsing failed or why 0 rows were detected"
            ),
        ),
    ]
