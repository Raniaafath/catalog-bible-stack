from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("importer", "0020_rename_attributemapping_importcolumnmapping"),
    ]

    operations = [
        migrations.AddField(
            model_name="productimport",
            name="category",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Product type / category assigned during import setup.",
                max_length=255,
            ),
        ),
    ]
