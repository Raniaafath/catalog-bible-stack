"""
Translation processor service.

Provides reusable translation logic that can be called from both
management commands and API views.
"""

import json
import logging
import os
from typing import List, Optional, Tuple

from django.db import transaction
from django.utils import timezone

from catalog.models import Attribute, AttributeValue, ProductAttributeValue, ProductType
from content.models import (
    AttributeI18n,
    AttributeValueI18n,
    Locale,
    ProductAttributeValueI18n,
    ProductTypeI18n,
    TranslationTask,
)

logger = logging.getLogger(__name__)


def process_translation_task(task_id: int) -> bool:
    """
    Process a single translation task by ID.
    
    This function can be called from:
    - Management command (run_translation_tasks)
    - API view (after task creation)
    - Background worker (celery, etc.)
    
    Returns:
        True if processing succeeded, False if it failed.
    """
    try:
        task = TranslationTask.objects.get(id=task_id)
    except TranslationTask.DoesNotExist:
        logger.error(f"TranslationTask {task_id} not found")
        return False
    
    # Get or create the target locale
    target_locale, _ = Locale.objects.get_or_create(
        code=task.locale,
        defaults={"name": task.locale}
    )
    
    return _process_task(task, target_locale)


def _process_task(task: TranslationTask, target_locale: Locale) -> bool:
    """
    Process a translation task with progress tracking.
    
    Returns:
        True if processing succeeded, False if it failed.
    """
    # Mark as in progress
    task.status = TranslationTask.Status.IN_PROGRESS
    task.started_at = timezone.now()
    task.save(update_fields=["status", "started_at", "updated_at"])
    
    try:
        warning: Optional[str] = None
        
        if task.scope == "attribute":
            items = _fetch_attributes(task.target_ids)
            task.items_total = len(items)
            task.save(update_fields=["items_total", "updated_at"])
            
            translations, warning = _translate_batch(items, target_locale.code, task)
            _upsert_attribute_i18n(translations, target_locale)
            task.items_completed = len(translations)
            
        elif task.scope == "attribute_value":
            items = _fetch_attribute_values(task.target_ids)
            task.items_total = len(items)
            task.save(update_fields=["items_total", "updated_at"])
            
            translations, warning = _translate_batch(items, target_locale.code, task)
            _upsert_attribute_value_i18n(translations, target_locale)
            task.items_completed = len(translations)
            
        elif task.scope == "product_type":
            items = _fetch_product_types(task.target_ids)
            task.items_total = len(items)
            task.save(update_fields=["items_total", "updated_at"])
            
            label_items = [(rid, label) for rid, label, _mc in items]
            mc_items = [(rid, mc) for rid, _label, mc in items]
            translations, warning = _translate_batch(label_items, target_locale.code, task)
            mc_translations, mc_warning = _translate_batch(mc_items, target_locale.code, task)
            
            warning = mc_warning if mc_warning and not warning else warning
            if mc_warning and warning and mc_warning != warning:
                warning = f"{warning} | {mc_warning}"
            
            _upsert_product_type_i18n(translations, mc_translations, target_locale)
            task.items_completed = len(translations)
            
        elif task.scope == "product_attribute_value":
            items = _fetch_product_attribute_values(task.target_ids)
            task.items_total = len(items)
            task.save(update_fields=["items_total", "updated_at"])
            
            translations, warning = _translate_batch(items, target_locale.code, task)
            _upsert_product_attribute_value_i18n(translations, target_locale)
            task.items_completed = len(translations)
            
            # Automatically translate attribute names if they're not already translated
            attribute_ids_to_translate = _get_missing_attribute_translations(task.target_ids, target_locale)
            if attribute_ids_to_translate:
                attr_items = _fetch_attributes(attribute_ids_to_translate)
                attr_translations, attr_warning = _translate_batch(attr_items, target_locale.code, task)
                _upsert_attribute_i18n(attr_translations, target_locale)
                if attr_warning:
                    warning = f"{warning} | Attribute names: {attr_warning}" if warning else f"Attribute names: {attr_warning}"
        else:
            raise ValueError(f"Unknown scope: {task.scope}")
            
    except Exception as exc:
        task.status = TranslationTask.Status.FAILED
        task.error = str(exc)
        task.finished_at = timezone.now()
        task.save(update_fields=["status", "error", "finished_at", "updated_at"])
        logger.error(f"Task {task.id} failed: {exc}")
        return False
    
    # Mark as done
    task.status = TranslationTask.Status.DONE
    task.error = warning or ""
    task.finished_at = timezone.now()
    task.save(update_fields=["status", "error", "items_completed", "finished_at", "updated_at"])
    
    if warning:
        logger.warning(f"Task {task.id} done with warning: {warning}")
    else:
        logger.info(f"Task {task.id} done ({task.scope}, {task.items_completed} items)")
    
    return True


def _fetch_attributes(ids: List[int]) -> List[Tuple[int, str]]:
    """Fetch attributes to translate."""
    if not ids:
        # If no specific IDs, get all translatable attributes
        rows = Attribute.objects.filter(is_value_translatable=True).values_list("id", "code")
    else:
        rows = Attribute.objects.filter(id__in=ids).values_list("id", "code")
    
    # Try to get French labels as source
    attr_ids = [rid for rid, _ in rows]
    fr_labels = {
        row["attribute_id"]: row["label"]
        for row in AttributeI18n.objects.filter(attribute_id__in=attr_ids, locale__code="fr").values("attribute_id", "label")
    }
    return [(rid, fr_labels.get(rid) or code) for rid, code in rows]


def _fetch_attribute_values(ids: List[int]) -> List[Tuple[int, str]]:
    """Fetch attribute values to translate."""
    if not ids:
        rows = list(AttributeValue.objects.all().values_list("id", "code"))
    else:
        rows = list(AttributeValue.objects.filter(id__in=ids).values_list("id", "code"))
    
    av_ids = [rid for rid, _ in rows]
    fr_map = dict(
        AttributeValueI18n.objects.filter(attribute_value_id__in=av_ids, locale__code="fr")
        .values_list("attribute_value_id", "label")
    )
    return [(rid, fr_map.get(rid) or code) for rid, code in rows]


def _fetch_product_types(ids: List[int]) -> List[Tuple[int, str, str]]:
    """Fetch product types to translate."""
    if not ids:
        rows = ProductType.objects.all().values_list("id", "default_label", "code", "main_category")
    else:
        rows = ProductType.objects.filter(id__in=ids).values_list("id", "default_label", "code", "main_category")
    
    result = []
    for rid, label, code, main_cat in rows:
        base = label or code
        mc = main_cat or base
        result.append((rid, base, mc))
    return result


def _fetch_product_attribute_values(ids: List[int]) -> List[Tuple[int, str]]:
    """Fetch product attribute values to translate."""
    if not ids:
        # Get all attributes that are translatable
        translatable_attrs = Attribute.objects.filter(is_value_translatable=True)
        rows = ProductAttributeValue.objects.filter(
            attribute__in=translatable_attrs
        ).select_related("attribute", "attribute_value").values_list("id", "value_text", "attribute_value__code")
    else:
        # Filter by specific attribute IDs
        rows = ProductAttributeValue.objects.filter(
            attribute_id__in=ids
        ).select_related("attribute", "attribute_value").values_list("id", "value_text", "attribute_value__code")
    
    values: List[Tuple[int, str]] = []
    for rid, value_text, av_code in rows:
        # Use value_text if available, otherwise use attribute_value code
        text = value_text or av_code or ""
        if not text:
            continue
        text = text.strip()
        if len(text) < 2 or text.lower() in {"-", "—", "n/a", "na"}:
            continue
        values.append((rid, text))
    return values


def _get_missing_attribute_translations(attribute_ids: List[int], target_locale: Locale) -> List[int]:
    """Get attribute IDs that don't have translations in the target locale yet."""
    if not attribute_ids:
        # If no specific attributes, get all translatable attributes
        all_attrs = Attribute.objects.filter(is_value_translatable=True).values_list("id", flat=True)
        attribute_ids = list(all_attrs)
    
    # Find which attributes already have translations
    existing_translations = set(
        AttributeI18n.objects.filter(
            attribute_id__in=attribute_ids,
            locale=target_locale
        ).values_list("attribute_id", flat=True)
    )
    
    # Return attributes that need translation
    return [attr_id for attr_id in attribute_ids if attr_id not in existing_translations]


def _translate_batch(
    items: List[Tuple[int, str]], target_locale_code: str, task: TranslationTask
) -> Tuple[List[Tuple[int, str]], Optional[str]]:
    """
    Translate a batch of items using OpenAI API.
    
    Falls back to source text if API key is missing or translation fails.
    """
    if not items:
        return ([], None)
    
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
    # Use task.model if set, otherwise fall back to environment variable
    model_name = task.model if task.model else os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    try:
        response = client.chat.completions.create(
            model=model_name,
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
def _upsert_attribute_i18n(translations: List[Tuple[int, str]], locale: Locale):
    """Upsert attribute translations."""
    for attr_id, label in translations:
        obj, created = AttributeI18n.objects.get_or_create(
            attribute_id=attr_id, locale=locale, defaults={"label": label}
        )
        if not created and obj.label != label:
            obj.label = label
            obj.save(update_fields=["label"])


@transaction.atomic
def _upsert_attribute_value_i18n(translations: List[Tuple[int, str]], locale: Locale):
    """Upsert attribute value translations."""
    for av_id, label in translations:
        obj, created = AttributeValueI18n.objects.get_or_create(
            attribute_value_id=av_id, locale=locale, defaults={"label": label}
        )
        if not created and obj.label != label:
            obj.label = label
            obj.save(update_fields=["label"])


@transaction.atomic
def _upsert_product_type_i18n(
    translations: List[Tuple[int, str]], mc_translations: List[Tuple[int, str]], locale: Locale
):
    """Upsert product type translations."""
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
def _upsert_product_attribute_value_i18n(translations: List[Tuple[int, str]], locale: Locale):
    """Upsert product attribute value translations."""
    for pav_id, value_text in translations:
        obj, created = ProductAttributeValueI18n.objects.get_or_create(
            product_attribute_value_id=pav_id, locale=locale, defaults={"value_text": value_text}
        )
        if not created and obj.value_text != value_text:
            obj.value_text = value_text
            obj.save(update_fields=["value_text"])
