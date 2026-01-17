import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pub", "0005_template_versioning"),
        ("content", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AttributeValueSynonym",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("term", models.CharField(max_length=255)),
                ("source", models.CharField(blank=True, max_length=50)),
                ("score", models.DecimalField(blank=True, decimal_places=4, max_digits=9, null=True)),
                ("status", models.CharField(choices=[("suggested", "Suggested"), ("approved", "Approved"), ("rejected", "Rejected")], default="suggested", max_length=20)),
                ("reason", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("attribute_value", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="synonyms", to="catalog.attributevalue")),
                ("channel", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="attribute_value_synonyms", to="pub.channel")),
                ("locale", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="attribute_value_synonyms", to="content.locale")),
            ],
            options={
                "indexes": [
                    models.Index(fields=["attribute_value", "locale", "channel", "status"], name="idx_attr_syn_locale_status")
                ],
                "constraints": [
                    models.UniqueConstraint(fields=("attribute_value", "locale", "channel", "term"), name="uniq_attr_value_synonym")
                ],
            },
        ),
    ]
