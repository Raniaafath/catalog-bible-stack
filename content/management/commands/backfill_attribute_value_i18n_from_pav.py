"""
Backfill AttributeValueI18n from existing ProductAttributeValueI18n rows.

Title generation looks up translated labels by attribute_value_id (AttributeValueI18n).
When translations are stored only in ProductAttributeValueI18n (per-PAV), titles
for variants whose PAVs weren't in the translated set still show the raw value.

This command copies translations from ProductAttributeValueI18n to AttributeValueI18n
for every PAV that has an attribute_value_id (enum), so one row per (attribute_value_id, locale)
covers all variants using that value.

Run once after you have ProductAttributeValueI18n data and before generating titles:
  python manage.py backfill_attribute_value_i18n_from_pav
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from catalog.models import ProductAttributeValue
from content.models import AttributeValueI18n, ProductAttributeValueI18n


class Command(BaseCommand):
    help = (
        "Copy ProductAttributeValueI18n translations to AttributeValueI18n for enum PAVs "
        "so title generation finds them for any variant."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only report what would be created/updated.",
        )
        parser.add_argument(
            "--locale",
            type=str,
            default=None,
            help="Limit to this locale code (e.g. de-DE). Default: all locales.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        locale_code = options.get("locale")
        qs = ProductAttributeValueI18n.objects.filter(
            product_attribute_value__attribute_value_id__isnull=False
        )
        if locale_code:
            qs = qs.filter(locale__code=locale_code)
        rows = list(
            qs.values_list("product_attribute_value_id", "locale_id", "value_text")
        )
        pav_ids = list({pav_id for pav_id, _, _ in rows})
        pav_to_av = dict(
            ProductAttributeValue.objects.filter(id__in=pav_ids).values_list(
                "id", "attribute_value_id"
            )
        )
        count = 0
        # (attribute_value_id, locale_id) -> value_text (first seen wins for dedupe)
        to_upsert = {}
        for pav_id, locale_id, value_text in rows:
            av_id = pav_to_av.get(pav_id)
            if not av_id:
                continue
            text = (value_text or "").strip()
            if not text:
                continue
            key = (av_id, locale_id)
            if key not in to_upsert:
                to_upsert[key] = text
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"Would upsert {len(to_upsert)} AttributeValueI18n row(s) (dry-run)."
                )
            )
            return
        with transaction.atomic():
            for (attribute_value_id, locale_id), label in to_upsert.items():
                obj, created = AttributeValueI18n.objects.get_or_create(
                    attribute_value_id=attribute_value_id,
                    locale_id=locale_id,
                    defaults={"label": label},
                )
                if not created and obj.label != label:
                    obj.label = label
                    obj.save(update_fields=["label"])
                    count += 1
                elif created:
                    count += 1
        self.stdout.write(
            self.style.SUCCESS(f"Upserted {count} AttributeValueI18n row(s).")
        )
