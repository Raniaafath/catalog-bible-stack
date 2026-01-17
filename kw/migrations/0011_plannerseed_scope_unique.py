from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kw", "0010_attributemap_origin_run_keyword_and_more"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="plannerseed",
            name="uniq_planner_seed_locale_normalized",
        ),
        migrations.AddConstraint(
            model_name="plannerseed",
            constraint=models.UniqueConstraint(
                fields=["locale", "product_type", "channel", "normalized_term"],
                name="uniq_planner_seed_scope_normalized",
            ),
        ),
    ]
