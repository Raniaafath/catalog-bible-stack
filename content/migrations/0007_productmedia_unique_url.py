from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0006_synonym_provenance_and_ordering"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="productmedia",
            constraint=models.UniqueConstraint(
                fields=["product", "url"],
                name="uniq_product_media_url",
            ),
        ),
    ]
