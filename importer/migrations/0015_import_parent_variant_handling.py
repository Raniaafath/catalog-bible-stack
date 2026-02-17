# Generated migration for parent-variant handling

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('importer', '0003_alter_productimport_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='importcolumnrule',
            name='is_variation_axis',
            field=models.BooleanField(default=False, help_text='Mark this attribute as a variation axis for generating variants'),
        ),
        migrations.AddField(
            model_name='importcolumnrule',
            name='axis_priority',
            field=models.IntegerField(default=0, help_text='Priority/position of this variation axis (0-4 for up to 5 axes)'),
        ),
        migrations.AddField(
            model_name='importcolumnrule',
            name='variant_level',
            field=models.BooleanField(default=False, help_text='Whether this attribute belongs to variant level (not product level)'),
        ),
        migrations.AddField(
            model_name='importrow',
            name='parent_key',
            field=models.CharField(max_length=255, blank=True, default='', help_text='Key to group variants under the same parent product'),
        ),
        migrations.AddField(
            model_name='importrow',
            name='is_parent',
            field=models.BooleanField(default=False, help_text='Whether this row represents a parent product'),
        ),
        migrations.AddIndex(
            model_name='importrow',
            index=models.Index(fields=['product_import', 'parent_key'], name='idx_import_row_parent_key'),
        ),
    ]
