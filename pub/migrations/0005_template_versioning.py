import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Q
from django.utils import timezone


def migrate_attribute_parts_forward(apps, schema_editor):
    TemplatePart = apps.get_model("pub", "TemplatePart")
    TemplatePart.objects.filter(part_type="attribute").update(part_type="attribute_value")


def migrate_attribute_parts_backward(apps, schema_editor):
    TemplatePart = apps.get_model("pub", "TemplatePart")
    TemplatePart.objects.filter(part_type="attribute_value").update(part_type="attribute")


class Migration(migrations.Migration):

    dependencies = [
        ("pub", "0004_channel_policies"),
    ]

    operations = [
        migrations.AlterField(
            model_name="template",
            name="channel",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="templates", to="pub.channel"),
        ),
        migrations.AlterField(
            model_name="template",
            name="product_type",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="templates", to="catalog.producttype"),
        ),
        migrations.AddField(
            model_name="template",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=timezone.now),
            preserve_default=False,
        ),
        migrations.AddConstraint(
            model_name="template",
            constraint=models.UniqueConstraint(
                condition=Q(("status", "active")),
                fields=("product_type", "locale", "channel", "kind"),
                name="uniq_active_template_scope",
            ),
        ),
        migrations.AlterField(
            model_name="templatepart",
            name="keyword_role",
            field=models.CharField(
                blank=True,
                choices=[("head", "Head"), ("hook", "Hook"), ("supporting", "Supporting")],
                max_length=20,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="templatepart",
            name="part_type",
            field=models.CharField(
                choices=[
                    ("keyword", "Keyword"),
                    ("axis_attribute", "Axis Attribute"),
                    ("attribute_value", "Attribute Value"),
                    ("literal", "Literal"),
                    ("brand", "Brand"),
                ],
                max_length=20,
            ),
        ),
        migrations.RunPython(
            migrate_attribute_parts_forward, migrate_attribute_parts_backward, elidable=True
        ),
        migrations.RemoveConstraint(
            model_name="templatepart",
            name="chk_part_attribute_requires_attr",
        ),
        migrations.AddConstraint(
            model_name="templatepart",
            constraint=models.CheckConstraint(
                condition=(
                    Q(("part_type__in", ["attribute_value", "axis_attribute"]))
                    & Q(("attribute__isnull", False))
                )
                | ~Q(("part_type__in", ["attribute_value", "axis_attribute"])),
                name="chk_part_attribute_requires_attr",
            ),
        ),
    ]
