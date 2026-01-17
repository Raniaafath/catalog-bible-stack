from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0004_product_core_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="variant",
            name="barcode",
            field=models.CharField(blank=True, db_index=True, max_length=32, null=True),
        ),
        migrations.AddField(
            model_name="variant",
            name="mpn",
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AddConstraint(
            model_name="variant",
            constraint=models.UniqueConstraint(
                condition=Q(("barcode__isnull", False), ("barcode", ""), _connector="AND", _negated=True),
                fields=("barcode",),
                name="uniq_variant_barcode",
            ),
        ),
    ]
