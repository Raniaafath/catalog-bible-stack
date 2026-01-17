from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pub", "0008_rename_pub_titlese_product_8020a2_idx_pub_titlese_product_16b3bf_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="channellocalepolicy",
            name="title_mode",
            field=models.CharField(
                choices=[("auto", "Auto"), ("review", "Review")],
                default="auto",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="channellocalepolicy",
            name="auto_create_selection",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="channellocalepolicy",
            name="auto_approve_selection",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="channellocalepolicy",
            name="selection_scope",
            field=models.CharField(
                choices=[("product", "Product"), ("variant", "Variant")],
                default="product",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="channellocalepolicy",
            name="context",
            field=models.CharField(default="title", max_length=50),
        ),
        migrations.AddField(
            model_name="channellocalepolicy",
            name="rules_json",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.RunSQL(
            sql="ALTER TABLE pub_channellocalepolicy DROP CONSTRAINT IF EXISTS uniq_channel_locale_policy;",
            reverse_sql="",
        ),
        migrations.AddConstraint(
            model_name="channellocalepolicy",
            constraint=models.UniqueConstraint(
                fields=("policy_set", "locale", "context"),
                name="uniq_channel_locale_policy_context",
            ),
        ),
        migrations.AddField(
            model_name="titleselection",
            name="context",
            field=models.CharField(default="title", max_length=50),
        ),
        migrations.AddField(
            model_name="titleselection",
            name="created_by_type",
            field=models.CharField(
                choices=[("system", "System"), ("user", "User")],
                default="system",
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name="titleselection",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("approved", "Approved"),
                    ("rejected", "Rejected"),
                    ("archived", "Archived"),
                ],
                default="draft",
                max_length=16,
            ),
        ),
        migrations.RunSQL(
            sql="ALTER TABLE pub_titleselection DROP CONSTRAINT IF EXISTS uniq_title_selection_scope;",
            reverse_sql="",
        ),
        migrations.AddConstraint(
            model_name="titleselection",
            constraint=models.UniqueConstraint(
                fields=("product", "variant", "locale", "channel", "context"),
                name="uniq_title_selection_scope_context",
            ),
        ),
        migrations.AddIndex(
            model_name="titleselection",
            index=models.Index(
                fields=["product", "locale", "channel", "context"],
                name="idx_title_selection_scope",
            ),
        ),
    ]
