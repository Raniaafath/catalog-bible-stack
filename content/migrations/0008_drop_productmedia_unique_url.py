from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0007_productmedia_unique_url"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="productmedia",
            name="uniq_product_media_url",
        ),
    ]
