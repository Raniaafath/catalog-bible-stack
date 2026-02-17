"""
Translation processor service.

Provides reusable translation logic that can be called from both
management commands and API views. Translations are produced for
multi-language catalogs using terminology most commonly used in the
target country/region for the relevant product type and field (e.g.
search-friendly, local e-commerce usage), not generic dictionary
equivalents.
"""

import json
import logging
import os
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

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

# Locale code -> (country/region name, language name) for translation instructions.
# Ensures we ask for "most common in that country" terminology. Add more as needed.
LOCALE_COUNTRY_HINTS: Dict[str, Tuple[str, str]] = {
    "de": ("Germany", "German"),
    "de-DE": ("Germany", "German"),
    "de-AT": ("Austria", "German"),
    "de-CH": ("Switzerland", "German"),
    "en": ("international English", "English"),
    "en-GB": ("United Kingdom", "British English"),
    "en-US": ("United States", "American English"),
    "fr": ("France", "French"),
    "fr-FR": ("France", "French"),
    "fr-BE": ("Belgium", "French"),
    "fr-CH": ("Switzerland", "French"),
    "es": ("Spain", "Spanish"),
    "es-ES": ("Spain", "Spanish"),
    "es-MX": ("Mexico", "Spanish"),
    "it": ("Italy", "Italian"),
    "it-IT": ("Italy", "Italian"),
    "nl": ("Netherlands", "Dutch"),
    "nl-NL": ("Netherlands", "Dutch"),
    "nl-BE": ("Belgium", "Dutch"),
    "pl": ("Poland", "Polish"),
    "pt": ("Portugal", "Portuguese"),
    "pt-BR": ("Brazil", "Brazilian Portuguese"),
}


def _get_locale_country_instruction(target_locale_code: str) -> str:
    """Return a short instruction for the target country/region (for prompts)."""
    code = (target_locale_code or "").strip()
    hint = LOCALE_COUNTRY_HINTS.get(code) or LOCALE_COUNTRY_HINTS.get(code.split("-")[0])
    if hint:
        country, language = hint
        return f"for {country} ({language}, {code}). Use the terminology most commonly used by shoppers and search in that country for this product category/field—not generic dictionary translations."
    return f"for the target locale {code}. Use the terminology most commonly used by shoppers and search in that country/region for this product category/field—not generic dictionary translations."


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

            translations, warning = _translate_batch(
                items, target_locale.code, task, context_extra={"scope": "attribute"}
            )
            _upsert_attribute_i18n(translations, target_locale)
            task.items_completed = len(translations)

        elif task.scope == "attribute_value":
            rich_items = _fetch_attribute_values(task.target_ids)
            task.items_total = len(rich_items)
            task.save(update_fields=["items_total", "updated_at"])

            all_translations: List[Tuple[int, str]] = []
            by_attr: Dict[str, List[Tuple[int, str]]] = defaultdict(list)
            for av_id, label, attr_code in rich_items:
                by_attr[attr_code].append((av_id, label))

            for attr_code, group in by_attr.items():
                tr, w = _translate_batch(
                    group,
                    target_locale.code,
                    task,
                    context_extra={"scope": "attribute_value", "attribute_code": attr_code},
                )
                all_translations.extend(tr)
                if w and not warning:
                    warning = w
                elif w and warning and w != warning:
                    warning = f"{warning} | {w}"
            _upsert_attribute_value_i18n(all_translations, target_locale)
            task.items_completed = len(all_translations)

        elif task.scope == "product_type":
            items = _fetch_product_types(task.target_ids)
            task.items_total = len(items)
            task.save(update_fields=["items_total", "updated_at"])

            label_items = [(rid, label) for rid, label, _mc in items]
            mc_items = [(rid, mc) for rid, _label, mc in items]
            translations, warning = _translate_batch(
                label_items, target_locale.code, task, context_extra={"scope": "product_type"}
            )
            mc_translations, mc_warning = _translate_batch(
                mc_items, target_locale.code, task, context_extra={"scope": "product_type"}
            )
            warning = mc_warning if mc_warning and not warning else warning
            if mc_warning and warning and mc_warning != warning:
                warning = f"{warning} | {mc_warning}"

            _upsert_product_type_i18n(translations, mc_translations, target_locale)
            task.items_completed = len(translations)

        elif task.scope == "product_attribute_value":
            rich_items = _fetch_product_attribute_values(task.target_ids)
            task.items_total = len(rich_items)
            task.save(update_fields=["items_total", "updated_at"])

            by_context: Dict[Tuple[str, str], List[Tuple[int, str]]] = defaultdict(list)
            for pav_id, text, attr_code, pt_label in rich_items:
                by_context[(attr_code, pt_label)].append((pav_id, text))

            all_translations = []
            for (attr_code, pt_label), group in by_context.items():
                tr, w = _translate_batch(
                    group,
                    target_locale.code,
                    task,
                    context_extra={
                        "scope": "product_attribute_value",
                        "attribute_code": attr_code,
                        "product_type_label": pt_label,
                    },
                )
                all_translations.extend(tr)
                if w and not warning:
                    warning = w
                elif w and warning and w != warning:
                    warning = f"{warning} | {w}"
            _upsert_product_attribute_value_i18n(all_translations, target_locale)
            # Also sync enum value translations to AttributeValueI18n so title generation
            # finds them for any variant (title renderer looks up by attribute_value_id).
            _sync_pav_translations_to_attribute_value_i18n(all_translations, target_locale)
            task.items_completed = len(all_translations)
            
            # Automatically translate attribute names if they're not already translated
            attribute_ids_to_translate = _get_missing_attribute_translations(task.target_ids, target_locale)
            if attribute_ids_to_translate:
                attr_items = _fetch_attributes(attribute_ids_to_translate)
                attr_translations, attr_warning = _translate_batch(
                    attr_items, target_locale.code, task, context_extra={"scope": "attribute"}
                )
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


def _fetch_attribute_values(ids: List[int]) -> List[Tuple[int, str, str]]:
    """Fetch attribute values to translate. Returns (av_id, label, attribute_code)."""
    if not ids:
        rows = list(
            AttributeValue.objects.select_related("attribute").values_list("id", "code", "attribute__code")
        )
    else:
        rows = list(
            AttributeValue.objects.filter(id__in=ids)
            .select_related("attribute")
            .values_list("id", "code", "attribute__code")
        )

    av_ids = [r[0] for r in rows]
    fr_map = dict(
        AttributeValueI18n.objects.filter(attribute_value_id__in=av_ids, locale__code="fr").values_list(
            "attribute_value_id", "label"
        )
    )
    return [(r[0], fr_map.get(r[0]) or r[1], r[2] or "") for r in rows]


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


def _fetch_product_attribute_values(ids: List[int]) -> List[Tuple[int, str, str, str]]:
    """Fetch product attribute values to translate. Returns (pav_id, text, attribute_code, product_type_label)."""
    if not ids:
        translatable_attrs = Attribute.objects.filter(is_value_translatable=True)
        qs = ProductAttributeValue.objects.filter(attribute__in=translatable_attrs).select_related(
            "attribute", "attribute_value", "product__product_type", "variant__product__product_type"
        )
    else:
        qs = ProductAttributeValue.objects.filter(attribute_id__in=ids).select_related(
            "attribute", "attribute_value", "product__product_type", "variant__product__product_type"
        )

    values: List[Tuple[int, str, str, str]] = []
    for pav in qs:
        text = (pav.value_text or (pav.attribute_value.code if pav.attribute_value else "") or "").strip()
        if not text or len(text) < 2 or text.lower() in {"-", "—", "n/a", "na"}:
            continue
        attr_code = pav.attribute.code if pav.attribute else ""
        if pav.variant_id and pav.variant.product_id:
            pt = getattr(pav.variant.product, "product_type", None)
        else:
            pt = getattr(pav.product, "product_type", None) if pav.product_id else None
        pt_label = (pt.default_label or pt.code) if pt else ""
        values.append((pav.id, text, attr_code, pt_label))
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


def _build_translation_prompts(
    target_locale_code: str,
    scope: str,
    context_extra: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str]:
    """Build system and user prompt for country-aware, product-type-aware translation (multi-language catalog)."""
    locale_instruction = _get_locale_country_instruction(target_locale_code)
    ctx = context_extra or {}

    system = (
        "You are a product catalog translator for multi-language e-commerce. "
        "Translate using the terminology most commonly used by shoppers and search engines in the target country/region "
        "for the given product category and field—not generic dictionary translations. "
        "Output must be suitable for a multi-language catalog (clear, consistent, search-friendly in that locale)."
    )

    scope_hint = ""
    if scope == "attribute":
        scope_hint = "Translate these attribute names (e.g. size, color, material) as they appear in e-commerce in the target country."
    elif scope == "attribute_value":
        attr = ctx.get("attribute_code") or "this attribute"
        scope_hint = f"Translate these enum/option values for attribute «{attr}» as customers and search typically use them in the target country."
    elif scope == "product_type":
        scope_hint = "Translate these product type labels and main category text as commonly used in the target country for search and navigation."
    elif scope == "product_attribute_value":
        attr = ctx.get("attribute_code") or "attribute"
        pt = ctx.get("product_type_label") or "product"
        scope_hint = f"Translate these product attribute values for attribute «{attr}» in product type «{pt}» as most commonly used in the target country (search and everyday usage)."
    else:
        scope_hint = "Translate these catalog texts for the target locale."

    user_prefix = (
        f"Translate the following into the target language. Target: {locale_instruction}\n"
        f"{scope_hint}\n"
        "Return JSON only: {\"translations\": [\"...\", \"...\"]} with the same length and order as the input. No other text.\n"
    )
    return system, user_prefix


def translate_batch_openai(
    items: List[Tuple[int, str]],
    target_locale_code: str,
    model: Optional[str] = None,
    context_extra: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Tuple[int, str]], Optional[str]]:
    """
    Translate a batch of (id, text) items using OpenAI with country/product-type-aware prompts.
    Used by the translation task processor and by management commands. Multi-language catalog oriented.
    """
    if not items:
        return ([], None)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return ([(rid, text) for rid, text in items], "Missing OPENAI_API_KEY; used source text")

    try:
        from openai import OpenAI
    except ImportError:
        return ([(rid, text) for rid, text in items], "openai package not installed; used source text")

    scope = (context_extra or {}).get("scope") or "product_attribute_value"
    system_msg, user_prefix = _build_translation_prompts(target_locale_code, scope, context_extra)

    client = OpenAI(api_key=api_key)
    labels = [text for _, text in items]
    user_content = user_prefix + f"Texts: {json.dumps(labels, ensure_ascii=False)}"
    model_name = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_content},
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


def _translate_batch(
    items: List[Tuple[int, str]],
    target_locale_code: str,
    task: TranslationTask,
    context_extra: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Tuple[int, str]], Optional[str]]:
    """Delegate to translate_batch_openai with task.model."""
    return translate_batch_openai(
        items,
        target_locale_code,
        model=task.model or None,
        context_extra=context_extra,
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


def _sync_pav_translations_to_attribute_value_i18n(
    translations: List[Tuple[int, str]], locale: Locale
) -> None:
    """
    For PAVs that have an attribute_value_id (enum), write the same translation to
    AttributeValueI18n so title generation finds it for any variant (title renderer
    looks up by attribute_value_id; one row covers all PAVs using that value).
    """
    if not translations:
        return
    pav_ids = [pav_id for pav_id, _ in translations]
    pav_to_av: Dict[int, Optional[int]] = dict(
        ProductAttributeValue.objects.filter(id__in=pav_ids).values_list("id", "attribute_value_id")
    )
    seen_av: set = set()
    av_translations: List[Tuple[int, str]] = []
    for pav_id, value_text in translations:
        av_id = pav_to_av.get(pav_id)
        if av_id and av_id not in seen_av and (value_text or "").strip():
            seen_av.add(av_id)
            av_translations.append((av_id, (value_text or "").strip()))
    if av_translations:
        _upsert_attribute_value_i18n(av_translations, locale)
