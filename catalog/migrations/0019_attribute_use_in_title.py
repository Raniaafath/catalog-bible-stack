from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0018_remove_product_source_description_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='attribute',
            name='use_in_title',
            field=models.BooleanField(
                default=True,
                help_text='Include this attribute as a candidate in title templates. Uncheck for internal/operational attributes (e.g. stock_qty, barcode).',
            ),
        ),
    ]
