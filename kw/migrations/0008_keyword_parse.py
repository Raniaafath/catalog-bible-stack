from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kw", "0007_attribute_map_status_provenance"),
    ]

    operations = [
        migrations.CreateModel(
            name="KeywordParse",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tokens", models.JSONField(default=list)),
                ("phrases", models.JSONField(default=list)),
                ("detected", models.JSONField(default=dict)),
                ("source", models.CharField(blank=True, max_length=50)),
                ("confidence", models.DecimalField(blank=True, decimal_places=4, max_digits=5, null=True)),
                ("tagged_by", models.CharField(blank=True, max_length=50)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "keyword",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="parses", to="kw.keyword"),
                ),
            ],
            options={
                "indexes": [models.Index(fields=["keyword"], name="idx_keyword_parse_keyword")],
            },
        ),
    ]
