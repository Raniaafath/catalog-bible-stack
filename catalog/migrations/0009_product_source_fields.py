from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0008_replace_bad_constraint_with_single_slot"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="source_description",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="product",
            name="source_locale",
            field=models.CharField(blank=True, default="", max_length=15),
        ),
        migrations.AddField(
            model_name="product",
            name="source_sku",
            field=models.CharField(blank=True, default="", max_length=150),
        ),
        migrations.AddField(
            model_name="product",
            name="source_supplier",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="product",
            name="source_title",
            field=models.TextField(blank=True, default=""),
        ),
    ]
