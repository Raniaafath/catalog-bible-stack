import os
from collections import defaultdict
from typing import Dict, List, Tuple

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from catalog.models import Attribute, ProductAttributeValue
from content.models import Locale, ProductAttributeValueI18n
from content.services.translation_processor import translate_batch_openai


class Command(BaseCommand):
    help = (
        "Translate non-enum ProductAttributeValue.value_text into a target locale. "
        "Uses terminology most commonly used in that country for the product type/attribute (multi-language catalog)."
    )

    def add_arguments(self, parser):
        parser.add_argument("--locale", required=True, help="Target locale code, e.g. de-DE or en-GB")
        parser.add_argument("--limit", type=int, default=200, help="Max number of rows to translate in this run.")
        parser.add_argument("--product-type", help="Optional product type code filter.")
        parser.add_argument("--attribute", help="Optional attribute code filter (comma-separated).")
        parser.add_argument("--dry-run", action="store_true", help="Do not write translations.")

    def handle(self, *args, **options):
        target_locale_code = options["locale"]
        limit = options["limit"]
        product_type_code = options["product_type"]
        attribute_codes = options["attribute"]
        dry_run = options["dry_run"]

        target_locale, _ = Locale.objects.get_or_create(code=target_locale_code, defaults={"name": target_locale_code})

        pav_qs = (
            ProductAttributeValue.objects.filter(value_text__isnull=False)
            .exclude(value_text="")
            .filter(attribute_value__isnull=True, attribute__is_value_translatable=True)
            .exclude(attribute__data_type=Attribute.DataType.ENUM)
            .exclude(i18n__locale=target_locale)
        )
        if product_type_code:
            pav_qs = pav_qs.filter(
                Q(product__product_type__code=product_type_code)
                | Q(variant__product__product_type__code=product_type_code)
            )
        if attribute_codes:
            codes = [c.strip() for c in attribute_codes.split(",") if c.strip()]
            if codes:
                pav_qs = pav_qs.filter(attribute__code__in=codes)

        pav_qs = pav_qs.select_related(
            "attribute", "product__product_type", "variant__product__product_type"
        ).order_by("id")[:limit]

        rich_items: List[Tuple[int, str, str, str]] = []
        for pav in pav_qs:
            text = (pav.value_text or "").strip()
            if not text or len(text) < 2 or text.lower() in {"-", "—", "n/a", "na"}:
                continue
            attr_code = pav.attribute.code if pav.attribute else ""
            if pav.variant_id and getattr(pav.variant, "product", None):
                pt = getattr(pav.variant.product, "product_type", None)
            else:
                pt = getattr(pav.product, "product_type", None) if pav.product_id else None
            pt_label = (pt.default_label or getattr(pt, "code", "")) if pt else ""
            rich_items.append((pav.id, text, attr_code, pt_label))

        if not rich_items:
            self.stdout.write(self.style.WARNING("No non-enum ProductAttributeValue rows found to translate."))
            return

        by_context: Dict[Tuple[str, str], List[Tuple[int, str]]] = defaultdict(list)
        for pav_id, text, attr_code, pt_label in rich_items:
            by_context[(attr_code, pt_label)].append((pav_id, text))

        translated_total = 0
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        for (attr_code, pt_label), group in by_context.items():
            for chunk in self._chunks(group, size=30):
                translations, warning = translate_batch_openai(
                    chunk,
                    target_locale.code,
                    model=model,
                    context_extra={
                        "scope": "product_attribute_value",
                        "attribute_code": attr_code,
                        "product_type_label": pt_label,
                    },
                )
                if warning:
                    self.stdout.write(self.style.WARNING(warning))
                if dry_run:
                    translated_total += len(translations)
                    continue
                self._upsert_pav_i18n(translations, target_locale)
                translated_total += len(translations)

        self.stdout.write(self.style.SUCCESS(f"Translated {translated_total} values to {target_locale.code}."))

    def _chunks(self, items: List[Tuple[int, str]], *, size: int) -> List[List[Tuple[int, str]]]:
        return [items[i : i + size] for i in range(0, len(items), size)]

    @transaction.atomic
    def _upsert_pav_i18n(self, translations: List[Tuple[int, str]], locale: Locale):
        for pav_id, value_text in translations:
            obj, created = ProductAttributeValueI18n.objects.get_or_create(
                product_attribute_value_id=pav_id, locale=locale, defaults={"value_text": value_text}
            )
            if not created and obj.value_text != value_text:
                obj.value_text = value_text
                obj.save(update_fields=["value_text"])
