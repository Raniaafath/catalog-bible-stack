from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("kw", "0013_product_keyword_map"),
    ]

    operations = [
        migrations.AddField(
            model_name="productkeywordmap",
            name="attribute",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="product_keyword_maps",
                to="catalog.attribute",
            ),
        ),
        migrations.AddField(
            model_name="productkeywordmap",
            name="num_value",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=18, null=True),
        ),
        migrations.AddField(
            model_name="productkeywordmap",
            name="num_unit",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name="productkeywordmap",
            name="match_kind",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
        migrations.AddField(
            model_name="productkeywordmap",
            name="matched_text",
            field=models.TextField(blank=True),
        ),
    ]
