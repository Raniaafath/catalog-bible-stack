# Generated manually for listing group axes

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0016_add_channel_variant_axis'),
        ('pub', '0019_add_channel_listing'),
    ]

    operations = [
        migrations.CreateModel(
            name='ChannelListingAxis',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('position', models.IntegerField(default=0)),
                ('label_override', models.TextField(blank=True, null=True)),
                ('enabled', models.BooleanField(default=True, help_text='Whether this axis is enabled for this listing')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('attribute', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='channel_listing_axes', to='catalog.attribute')),
                ('listing', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='listing_axes', to='pub.channellisting')),
            ],
            options={
                'ordering': ['listing', 'position'],
                'indexes': [
                    models.Index(fields=['listing', 'position'], name='idx_listing_axis_position'),
                    models.Index(fields=['listing', 'enabled'], name='idx_listing_axis_enabled'),
                ],
                'constraints': [
                    models.UniqueConstraint(fields=['listing', 'attribute'], name='uniq_channel_listing_axis'),
                ],
            },
        ),
    ]
