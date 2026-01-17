import json
import os
from typing import List, Tuple, Optional

from django.core.management.base import BaseCommand
from django.db import transaction

from catalog.models import Attribute, AttributeValue, ProductAttributeValue, ProductType
from content.models import (
    AttributeI18n,
    AttributeValueI18n,
    Locale,
    ProductAttributeValueI18n,
    ProductTypeI18n,
    TranslationTask,
)


class Command(BaseCommand):
    help = "Process pending TranslationTask rows and upsert i18n labels. Uses a stub translator; wire to your MT/AI API."

    def add_arguments(self, parser):
        parser.add_argument("--locale", required=True, help="Target locale code, e.g. en or de")
        parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="Max number of tasks to process in this run.",
        )

    def handle(self, *args, **options):
        target_locale_code = options["locale"]
        limit = options["limit"]

        target_locale, _ = Locale.objects.get_or_create(code=target_locale_code, defaults={"name": target_locale_code})

        tasks = (
            TranslationTask.objects.filter(locale=target_locale.code, status=TranslationTask.Status.PENDING)
            .order_by("created_at")[:limit]
        )
        if not tasks:
            self.stdout.write(self.style.WARNING("No pending translation tasks"))
            return

        for task in tasks:
            self._process_task(task, target_locale)

    def _process_task(self, task: TranslationTask, target_locale: Locale):
        task.status = TranslationTask.Status.IN_PROGRESS
        task.save(update_fields=["status", "updated_at"])
        try:
            warning: Optional[str] = None
            if task.scope == "attribute":
                items = self._fetch_attributes(task.target_ids)
                translations, warning = self._translate_batch(items, target_locale.code)
                self._upsert_attribute_i18n(translations, target_locale)
            elif task.scope == "attribute_value":
                items = self._fetch_attribute_values(task.target_ids)
                translations, warning = self._translate_batch(items, target_locale.code)
                self._upsert_attribute_value_i18n(translations, target_locale)
            elif task.scope == "product_type":
                items = self._fetch_product_types(task.target_ids)
                label_items = [(rid, label) for rid, label, _mc in items]
                mc_items = [(rid, mc) for rid, _label, mc in items]
                translations, warning = self._translate_batch(label_items, target_locale.code)
                mc_translations, mc_warning = self._translate_batch(mc_items, target_locale.code)
                warning = mc_warning if mc_warning and not warning else warning
                if mc_warning and warning and mc_warning != warning:
                    warning = f"{warning} | {mc_warning}"
                self._upsert_product_type_i18n(translations, mc_translations, target_locale)
            elif task.scope == "product_attribute_value":
                items = self._fetch_product_attribute_values(task.target_ids)
                translations, warning = self._translate_batch(items, target_locale.code)
                self._upsert_product_attribute_value_i18n(translations, target_locale)
            else:
                raise ValueError(f"Unknown scope: {task.scope}")
        except Exception as exc:
            task.status = TranslationTask.Status.FAILED
            task.error = str(exc)
            task.save(update_fields=["status", "error", "updated_at"])
            self.stdout.write(self.style.ERROR(f"Task {task.id} failed: {exc}"))
            return

        task.status = TranslationTask.Status.DONE
        task.error = warning or ""
        task.save(update_fields=["status", "error", "updated_at"])
        if warning:
            self.stdout.write(self.style.WARNING(f"Task {task.id} done with warning: {warning}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Task {task.id} done ({task.scope}, {len(task.target_ids)} items)"))

    def _fetch_attributes(self, ids: List[int]) -> List[Tuple[int, str]]:
        rows = Attribute.objects.filter(id__in=ids).values_list("id", "code")
        fr_labels = {
            row["attribute_id"]: row["label"]
            for row in AttributeI18n.objects.filter(attribute_id__in=ids, locale__code="fr").values("attribute_id", "label")
        }
        return [(rid, fr_labels.get(rid) or code) for rid, code in rows]

    def _fetch_attribute_values(self, ids: List[int]) -> List[Tuple[int, str]]:
        rows = list(AttributeValue.objects.filter(id__in=ids).values_list("id", "code"))
        fr_map = dict(
            AttributeValueI18n.objects.filter(attribute_value_id__in=ids, locale__code="fr")
            .values_list("attribute_value_id", "label")
        )
        return [(rid, fr_map.get(rid) or code) for rid, code in rows]

    def _fetch_product_types(self, ids: List[int]) -> List[Tuple[int, str, str]]:
        rows = ProductType.objects.filter(id__in=ids).values_list("id", "default_label", "code", "main_category")
        result = []
        for rid, label, code, main_cat in rows:
            base = label or code
            mc = main_cat or base
            result.append((rid, base, mc))
        return result

    def _fetch_product_attribute_values(self, ids: List[int]) -> List[Tuple[int, str]]:
        rows = ProductAttributeValue.objects.filter(id__in=ids).values_list("id", "value_text")
        values: List[Tuple[int, str]] = []
        for rid, value in rows:
            if not value:
                continue
            text = value.strip()
            if len(text) < 3 or text.lower() in {"-", "—", "n/a", "na"}:
                continue
            values.append((rid, text))
        return values

    def _translate_batch(
        self, items: List[Tuple[int, str]], target_locale_code: str
    ) -> Tuple[List[Tuple[int, str]], Optional[str]]:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            # Fallback: echo source text if no key present.
            return ([(rid, text) for rid, text in items], "Missing OPENAI_API_KEY; used source text")

        try:
            from openai import OpenAI
        except ImportError:
            # If openai not installed in runtime, fallback to echo.
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
            # On any failure, fallback to source text to keep pipeline running, but surface the reason and content snippet.
            snippet = ""
            if "content" in locals():
                snippet = f" | content: {str(content)[:200]}"
            return (
                [(rid, text) for rid, text in items],
                f"OpenAI translation failed: {exc}{snippet}",
            )

    @transaction.atomic
    def _upsert_attribute_i18n(self, translations: List[Tuple[int, str]], locale: Locale):
        for attr_id, label in translations:
            obj, created = AttributeI18n.objects.get_or_create(
                attribute_id=attr_id, locale=locale, defaults={"label": label}
            )
            if not created and obj.label != label:
                obj.label = label
                obj.save(update_fields=["label"])

    @transaction.atomic
    def _upsert_attribute_value_i18n(self, translations: List[Tuple[int, str]], locale: Locale):
        for av_id, label in translations:
            obj, created = AttributeValueI18n.objects.get_or_create(
                attribute_value_id=av_id, locale=locale, defaults={"label": label}
            )
            if not created and obj.label != label:
                obj.label = label
                obj.save(update_fields=["label"])

    @transaction.atomic
    def _upsert_product_type_i18n(
        self, translations: List[Tuple[int, str]], mc_translations: List[Tuple[int, str]], locale: Locale
    ):
        mc_map = {pid: mc for pid, mc in mc_translations}
        for pt_id, label in translations:
            obj, created = ProductTypeI18n.objects.get_or_create(
                product_type_id=pt_id,
                locale=locale,
                defaults={"label": label, "main_category": mc_map.get(pt_id, "")},
            )
            if not created:
                updated_fields = []
                if obj.label != label:
                    obj.label = label
                    updated_fields.append("label")
                mc_value = mc_map.get(pt_id)
                if mc_value is not None and obj.main_category != mc_value:
                    obj.main_category = mc_value
                    updated_fields.append("main_category")
                if updated_fields:
                    obj.save(update_fields=updated_fields)

    @transaction.atomic
    def _upsert_product_attribute_value_i18n(self, translations: List[Tuple[int, str]], locale: Locale):
        for pav_id, value_text in translations:
            obj, created = ProductAttributeValueI18n.objects.get_or_create(
                product_attribute_value_id=pav_id, locale=locale, defaults={"value_text": value_text}
            )
            if not created and obj.value_text != value_text:
                obj.value_text = value_text
                obj.save(update_fields=["value_text"])
