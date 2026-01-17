import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0002_variant_internal_sku"),
    ]

    operations = [
        migrations.AddField(
            model_name="producttype",
            name="default_label",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="producttype",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="producttype",
            name="notes",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="producttype",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="children",
                to="catalog.producttype",
            ),
        ),
        migrations.AddField(
            model_name="producttype",
            name="sort_order",
            field=models.IntegerField(default=0),
        ),
    ]
