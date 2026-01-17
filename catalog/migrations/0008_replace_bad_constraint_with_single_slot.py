from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0007_attribute_value_constraints_indexes"),
    ]

    # No-op: constraint skipped due to existing data; can be reintroduced later after cleanup.
    operations = []
