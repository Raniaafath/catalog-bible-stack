import json
import os
from typing import List, Tuple, Optional

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from catalog.models import Attribute, ProductAttributeValue
from content.models import Locale, ProductAttributeValueI18n


class Command(BaseCommand):
    help = "Translate non-enum ProductAttributeValue.value_text into a target locale."

    def add_arguments(self, parser):
        parser.add_argument("--locale", required=True, help="Target locale code, e.g. en or de")
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

        pav_qs = pav_qs.select_related("attribute").order_by("id")[:limit]
        items = [(pav.id, pav.value_text) for pav in pav_qs]

        if not items:
            self.stdout.write(self.style.WARNING("No non-enum ProductAttributeValue rows found to translate."))
            return

        translated_total = 0
        for chunk in self._chunks(items, size=30):
            translations, warning = self._translate_batch(chunk, target_locale.code)
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

    def _translate_batch(
        self, items: List[Tuple[int, str]], target_locale_code: str
    ) -> Tuple[List[Tuple[int, str]], Optional[str]]:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return ([(rid, text) for rid, text in items], "Missing OPENAI_API_KEY; used source text")

        try:
            from openai import OpenAI
        except ImportError:
            return ([(rid, text) for rid, text in items], "openai package not installed; used source text")

        client = OpenAI(api_key=api_key)
        labels = [text for _, text in items]
        prompt = (
            "Translate the following texts into the target language.\n"
            f"Target language code: {target_locale_code}\n"
            "Return JSON in the shape: {\"translations\": [\"...\", \"...\"]} with the same length/order as input.\n"
            f"Texts: {json.dumps(labels, ensure_ascii=False)}"
        )
        try:
            response = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": "You are a concise product catalog translator."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            parsed = json.loads(content)
            translated_list = parsed.get("translations") if isinstance(parsed, dict) else None
            if not isinstance(translated_list, list) or len(translated_list) != len(labels):
                raise ValueError(f"Unexpected translation response shape: {content[:200]}")
            return ([(rid, translated_list[idx]) for idx, (rid, _) in enumerate(items)], None)
        except Exception as exc:
            snippet = ""
            if "content" in locals():
                snippet = f" | content: {str(content)[:200]}"
            return (
                [(rid, text) for rid, text in items],
                f"OpenAI translation failed: {exc}{snippet}",
            )

    @transaction.atomic
    def _upsert_pav_i18n(self, translations: List[Tuple[int, str]], locale: Locale):
        for pav_id, value_text in translations:
            obj, created = ProductAttributeValueI18n.objects.get_or_create(
                product_attribute_value_id=pav_id, locale=locale, defaults={"value_text": value_text}
            )
            if not created and obj.value_text != value_text:
                obj.value_text = value_text
                obj.save(update_fields=["value_text"])
