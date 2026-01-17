import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Q


def create_default_policy_sets(apps, schema_editor):
    Channel = apps.get_model("pub", "Channel")
    ChannelPolicySet = apps.get_model("pub", "ChannelPolicySet")
    ChannelConstraintPolicy = apps.get_model("pub", "ChannelConstraintPolicy")
    ChannelBundlePolicy = apps.get_model("pub", "ChannelBundlePolicy")

    db_alias = schema_editor.connection.alias

    for channel in Channel.objects.using(db_alias).all():
        policy_set, _ = ChannelPolicySet.objects.using(db_alias).get_or_create(
            channel=channel,
            version=1,
            defaults={"status": "active"},
        )
        ChannelConstraintPolicy.objects.using(db_alias).get_or_create(policy_set=policy_set)
        ChannelBundlePolicy.objects.using(db_alias).get_or_create(policy_set=policy_set)


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0002_variant_internal_sku"),
        ("content", "0001_initial"),
        ("pub", "0003_generation"),
    ]

    operations = [
        migrations.AddField(
            model_name="channel",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="channel",
            name="priority",
            field=models.IntegerField(default=0),
        ),
        migrations.CreateModel(
            name="ChannelPolicySet",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("version", models.IntegerField(default=1)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("active", "Active"), ("archived", "Archived")], default="draft", max_length=20)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("channel", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="policy_sets", to="pub.channel")),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("channel", "version"), name="uniq_channel_policy_set_version")
                ],
                "indexes": [models.Index(fields=["channel", "status"], name="idx_channel_policy_status")],
            },
        ),
        migrations.CreateModel(
            name="ChannelProductOption",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slot_index", models.PositiveSmallIntegerField()),
                ("code", models.CharField(blank=True, max_length=50)),
                ("option_kind", models.CharField(choices=[("attribute", "Attribute"), ("composite", "Composite"), ("literal", "Literal")], max_length=20)),
                ("label_default", models.CharField(blank=True, max_length=100)),
                ("literal_value", models.CharField(blank=True, max_length=200)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("channel", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="product_options", to="pub.channel")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="channel_options", to="catalog.product")),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("product", "channel", "slot_index"), name="uniq_channel_product_option_slot"),
                    models.CheckConstraint(condition=Q(("slot_index__gte", 1)) & Q(("slot_index__lte", 10)), name="chk_option_slot_index_range"),
                    models.CheckConstraint(
                        condition=Q(("option_kind", "literal")) & Q(("literal_value__isnull", False)) & ~Q(("literal_value", ""))
                        | ~Q(("option_kind", "literal")),
                        name="chk_option_literal_requires_value",
                    ),
                ]
            },
        ),
        migrations.CreateModel(
            name="ChannelLocalePolicy",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("country_code", models.CharField(blank=True, max_length=2)),
                ("currency_code", models.CharField(blank=True, max_length=3)),
                ("title_max_len", models.IntegerField(default=150)),
                ("meta_title_max_len", models.IntegerField(default=70)),
                ("meta_description_max_len", models.IntegerField(default=160)),
                ("description_max_len", models.IntegerField(default=5000)),
                ("bullet_count", models.IntegerField(default=5)),
                ("bullet_max_len", models.IntegerField(default=200)),
                ("title_separator", models.CharField(default=" – ", max_length=20)),
                ("brand_position", models.CharField(choices=[("start", "Start"), ("end", "End"), ("none", "None")], default="end", max_length=10)),
                ("normalize_whitespace", models.BooleanField(default=True)),
                ("dedupe_words", models.BooleanField(default=True)),
                ("banned_terms", models.JSONField(default=list)),
                ("policy_set", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="locale_policies", to="pub.channelpolicyset")),
                ("locale", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="channel_locale_policies", to="content.locale")),
            ],
            options={
                "constraints": [models.UniqueConstraint(fields=("policy_set", "locale"), name="uniq_channel_locale_policy")]
            },
        ),
        migrations.CreateModel(
            name="ChannelConstraintPolicy",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("max_variants", models.IntegerField(blank=True, null=True)),
                ("max_options", models.IntegerField(blank=True, null=True)),
                ("max_option_values", models.IntegerField(blank=True, null=True)),
                ("allow_bundles", models.BooleanField(default=True)),
                ("allow_multi_currency", models.BooleanField(default=True)),
                ("require_approval", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("policy_set", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="constraint_policy", to="pub.channelpolicyset")),
            ],
        ),
        migrations.CreateModel(
            name="ChannelBundlePolicy",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("bundle_title_mode", models.CharField(choices=[("parent_only", "Parent Only"), ("include_components", "Include Components"), ("include_counts", "Include Counts")], default="parent_only", max_length=30)),
                ("max_components_in_title", models.IntegerField(default=0)),
                ("show_components_in_bullets", models.BooleanField(default=True)),
                ("show_components_in_description", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("policy_set", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="bundle_policy", to="pub.channelpolicyset")),
            ],
        ),
        migrations.CreateModel(
            name="ChannelProductOptionI18n",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label", models.CharField(max_length=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("locale", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="channel_product_option_labels", to="content.locale")),
                ("option", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="i18n", to="pub.channelproductoption")),
            ],
            options={"constraints": [models.UniqueConstraint(fields=("option", "locale"), name="uniq_channel_product_option_i18n")]},
        ),
        migrations.CreateModel(
            name="ChannelProductOptionAttribute",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("position", models.IntegerField(default=0)),
                ("prefix", models.CharField(blank=True, max_length=20)),
                ("suffix", models.CharField(blank=True, max_length=20)),
                ("separator", models.CharField(blank=True, default="x", max_length=10)),
                ("unit_override", models.CharField(blank=True, max_length=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("attribute", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="channel_product_options", to="catalog.attribute")),
                ("option", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attributes", to="pub.channelproductoption")),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("option", "attribute"), name="uniq_channel_option_attribute"),
                    models.UniqueConstraint(fields=("option", "position"), name="uniq_channel_option_attribute_position"),
                ]
            },
        ),
        migrations.RunPython(create_default_policy_sets, reverse_code=migrations.RunPython.noop),
    ]
