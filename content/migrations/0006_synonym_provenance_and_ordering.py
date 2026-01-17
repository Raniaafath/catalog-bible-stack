import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kw", "0006_shorten_planner_run_keyword_indexes"),
        ("content", "0005_merge_synonyms_branches"),
    ]

    operations = [
        migrations.AddField(
            model_name="attributevaluesynonym",
            name="keyword",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.SET_NULL,
                related_name="value_synonyms",
                to="kw.keyword",
            ),
        ),
        migrations.AddField(
            model_name="attributevaluesynonym",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.RemoveIndex(
            model_name="attributevaluesynonym",
            name="idx_attr_syn_locale_status",
        ),
        migrations.AddIndex(
            model_name="attributevaluesynonym",
            index=models.Index(
                fields=["attribute_value", "locale", "channel", "status", "score"],
                name="idx_attr_syn_locale_status",
            ),
        ),
    ]
