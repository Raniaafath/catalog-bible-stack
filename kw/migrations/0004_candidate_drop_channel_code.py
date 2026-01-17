from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("kw", "0003_candidate_channel_data"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="candidate",
            name="uniq_candidate_scope_keyword_role",
        ),
        migrations.RemoveField(
            model_name="candidate",
            name="channel_code",
        ),
    ]
