# Generated migration to make ChannelListing.product optional

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pub', '0020_backfill_default_listings'),
        ('catalog', '0018_remove_product_source_description_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='channellisting',
            name='product',
            field=models.ForeignKey(
                blank=True,
                help_text='Product for this listing. If null, will be auto-assigned when variants are added.',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='channel_listings',
                to='catalog.product',
            ),
        ),
        migrations.AlterConstraint(
            model_name='channellisting',
            name='uniq_default_channel_listing',
            constraint=models.UniqueConstraint(
                condition=models.Q(('is_default', True), ('product__isnull', False)),
                fields=('product', 'channel', 'locale'),
                name='uniq_default_channel_listing',
            ),
        ),
    ]
