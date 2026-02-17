# Generated manually for listing groups

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pub', '0018_add_channel_variant_axis'),
        ('catalog', '0016_add_channel_variant_axis'),
        ('content', '0014_add_translation_task_model'),
    ]

    operations = [
        migrations.CreateModel(
            name='ChannelListing',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, help_text="Optional label like 'eBay – split by color'", max_length=200)),
                ('is_default', models.BooleanField(default=True, help_text='Whether this is the default listing for this product+channel+locale')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('channel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='product_listings', to='pub.channel')),
                ('locale', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='channel_listings', to='content.locale')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='channel_listings', to='catalog.product')),
            ],
            options={
                'ordering': ['product', 'channel', 'locale', '-is_default', 'name'],
                'indexes': [
                    models.Index(fields=['product', 'channel', 'locale'], name='idx_channel_listing_scope'),
                    models.Index(fields=['channel', 'is_default'], name='idx_channel_listing_default'),
                ],
                'constraints': [
                    models.UniqueConstraint(
                        fields=['product', 'channel', 'locale'],
                        condition=models.Q(('is_default', True)),
                        name='uniq_default_channel_listing',
                    ),
                ],
            },
        ),
        migrations.AddField(
            model_name='channellistingmap',
            name='listing',
            field=models.ForeignKey(
                blank=True,
                help_text='The listing group this variant belongs to (null = no specific listing)',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='variant_maps',
                to='pub.channellisting',
            ),
        ),
        migrations.AddIndex(
            model_name='channellistingmap',
            index=models.Index(fields=['listing'], name='idx_clm_listing'),
        ),
        migrations.AddIndex(
            model_name='channellistingmap',
            index=models.Index(fields=['variant', 'channel'], name='idx_clm_scope'),
        ),
        migrations.AddConstraint(
            model_name='channellistingmap',
            constraint=models.UniqueConstraint(
                condition=models.Q(('listing__isnull', False)),
                fields=['listing', 'variant'],
                name='uniq_listing_variant',
            ),
        ),
    ]
