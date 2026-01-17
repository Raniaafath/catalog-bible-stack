import uuid

from django.db import migrations, models
from django.utils import timezone


def backfill_product_codes(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    db_alias = schema_editor.connection.alias
    products = Product.objects.using(db_alias).filter(code__isnull=True)
    for product in products:
        product.code = f"product-{product.pk}" if product.pk else str(uuid.uuid4())
        product.save(update_fields=["code"])


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0003_producttype_structure"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="code",
            field=models.CharField(blank=True, max_length=150, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="product",
            name="default_label",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="product",
            name="series",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="product",
            name="status",
            field=models.CharField(choices=[("draft", "Draft"), ("active", "Active"), ("discontinued", "Discontinued")], default="draft", max_length=20),
        ),
        migrations.AddField(
            model_name="product",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=timezone.now),
            preserve_default=False,
        ),
        migrations.RunPython(backfill_product_codes, reverse_code=migrations.RunPython.noop),
        migrations.AlterField(
            model_name="product",
            name="code",
            field=models.CharField(max_length=150, unique=True),
        ),
    ]
