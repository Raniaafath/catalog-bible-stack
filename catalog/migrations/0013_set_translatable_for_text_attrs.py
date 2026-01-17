from django.db import migrations


def mark_text_attributes_translatable(apps, schema_editor):
    Attribute = apps.get_model("catalog", "Attribute")
    Attribute.objects.filter(data_type="text").update(is_value_translatable=True)


def undo_mark_text_attributes_translatable(apps, schema_editor):
    Attribute = apps.get_model("catalog", "Attribute")
    Attribute.objects.filter(data_type="text").update(is_value_translatable=False)


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0012_attribute_is_value_translatable"),
    ]

    operations = [
        migrations.RunPython(
            mark_text_attributes_translatable,
            reverse_code=undo_mark_text_attributes_translatable,
        ),
    ]
