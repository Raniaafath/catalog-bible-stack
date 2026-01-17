from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("pub", "0005_template_versioning"),
        ("kw", "0014_product_keyword_map_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="generationoutput",
            name="head_text",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="generationoutput",
            name="hook_text",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="generationoutput",
            name="head_source",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name="generationoutput",
            name="hook_source",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name="generationoutput",
            name="head_keyword",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="generation_head_outputs",
                to="kw.keyword",
            ),
        ),
        migrations.AddField(
            model_name="generationoutput",
            name="hook_keyword",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="generation_hook_outputs",
                to="kw.keyword",
            ),
        ),
    ]
