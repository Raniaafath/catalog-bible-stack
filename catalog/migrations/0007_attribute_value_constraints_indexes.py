from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0006_remove_variant_uniq_variant_barcode_and_more"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="productattributevalue",
            index=models.Index(fields=["attribute"], name="idx_pav_attribute"),
        ),
        migrations.AddIndex(
            model_name="productattributevalue",
            index=models.Index(
                fields=["attribute", "attribute_value"], name="idx_pav_attr_value"
            ),
        ),
    ]
