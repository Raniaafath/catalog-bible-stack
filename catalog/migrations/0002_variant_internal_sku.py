import uuid

from django.db import migrations, models


def populate_internal_sku(apps, schema_editor):
    Variant = apps.get_model("catalog", "Variant")
    db_alias = schema_editor.connection.alias
    variants = Variant.objects.using(db_alias).filter(internal_sku__isnull=True)
    for variant in variants:
        variant.internal_sku = str(uuid.uuid4())
        variant.save(update_fields=["internal_sku"])


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="variant",
            name="internal_sku",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.RunPython(populate_internal_sku, reverse_code=migrations.RunPython.noop),
        migrations.AlterField(
            model_name="variant",
            name="internal_sku",
            field=models.TextField(default=uuid.uuid4, unique=True),
        ),
    ]
