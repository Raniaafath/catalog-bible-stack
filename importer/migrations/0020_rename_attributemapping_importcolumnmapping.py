from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("importer", "0019_alter_importcolumnrule_role"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="AttributeMapping",
            new_name="ImportColumnMapping",
        ),
    ]
