import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pub", "0003_generation"),
        ("kw", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="candidate",
            name="channel",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="kw_candidates",
                to="pub.channel",
            ),
        ),
        migrations.AddIndex(
            model_name="candidate",
            index=models.Index(
                fields=["locale", "channel", "role", "status"],
                name="idx_candidate_locale_channel",
            ),
        ),
        migrations.AddConstraint(
            model_name="candidate",
            constraint=models.UniqueConstraint(
                condition=models.Q(("channel__isnull", False)),
                fields=("locale", "channel", "keyword", "role", "product", "variant"),
                name="uq_candidate_channel_fk",
            ),
        ),
    ]
