from __future__ import annotations

import json
import os
import re
from contextlib import nullcontext
from typing import Dict, List, Optional

from django.db import transaction
from django.db.models import Max, Q, QuerySet

from catalog.models import AttributeValue, Product, ProductAttributeValue
from content.models import AttributeValueI18n, Locale, ProductAttributeValueI18n, ProductI18n
from kw.management.commands.parse_keywords import _normalize_term, _ngram_tokens, _tokenize
from kw.stopwords import get_match_stopwords
from django.conf import settings
from kw.models import AttributeMap, KeywordParse, PlannerRun, PlannerRunKeyword, ProductKeywordMap, Keyword, Metric

_SPACE_RE = re.compile(r"\s+")

# Do not create a match when the matched phrase is shorter than this (avoids "r", "1", etc.).
_MIN_MATCH_PHRASE_LEN = 2

# Attribute codes treated as "size" when ignore_size_and_marketplace is True (no mappings created for these).
_SIZE_ATTRIBUTE_CODES: frozenset[str] = frozenset({
    "longueur_cm", "largeur_cm", "hauteur_cm", "profondeur_cm",
    "size", "taille", "dimension", "dimensions",
    "width", "height", "length", "depth", "length_cm", "width_cm", "height_cm",
})


def _is_size_attribute(attribute_code: Optional[str]) -> bool:
    if not attribute_code:
        return False
    code = (attribute_code or "").strip().lower()
    if code in _SIZE_ATTRIBUTE_CODES:
        return True
    if code.endswith("_cm") and any(code.startswith(p) for p in ("longueur", "largeur", "hauteur", "profondeur", "length", "width", "height", "depth")):
        return True
    return False


def _numeric_substring_false_match(keyword_term: str, value_code: Optional[str]) -> bool:
    """
    Return True if this enum match is likely wrong: value_code is numeric and appears
    as a strict substring of a longer number in the keyword (e.g. "10" in "110", "40" in "140").
    """
    if not value_code or not (str(value_code).strip().isdigit()):
        return False
    term = (keyword_term or "").strip()
    if not term:
        return False
    val = str(value_code).strip()
    num_tokens = re.findall(r"\d+", term)
    for token in num_tokens:
        if token != val and val in token:
            return True
    return False


def _debug_log_path():
    """Path for debug log (works in Docker when project is mounted at BASE_DIR)."""
    base = getattr(settings, "BASE_DIR", None)
    root = str(base) if base is not None else os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(root, ".cursor", "debug.log")


def _json_safe(val: object) -> object:
    """Return a JSON-serializable copy of val (for evidence dicts)."""
    if val is None:
        return None
    if isinstance(val, (str, int, float, bool)):
        return val
    if isinstance(val, dict):
        return {str(k): _json_safe(v) for k, v in val.items()}
    if isinstance(val, (list, tuple)):
        return [_json_safe(v) for v in val]
    return str(val)


def _normalize_phrase(text: str) -> str:
    return _SPACE_RE.sub(" ", (text or "").strip().lower())


def _normalize_whitespace(text: str) -> str:
    return _SPACE_RE.sub(" ", (text or "").strip())


def _phrases_from_term(term: str) -> List[str]:
    norm = _normalize_term(term)
    tokens = _tokenize(norm)
    phrases: List[str] = []
    for n in (1, 2, 3):
        phrases.extend(list(_ngram_tokens(tokens, n)))
    return phrases


def _phrases_from_texts(texts: List[str]) -> set[str]:
    phrases: set[str] = set()
    for text in texts:
        norm = _normalize_term(text or "")
        tokens = _tokenize(norm)
        for n in (1, 2, 3):
            for phrase in _ngram_tokens(tokens, n):
                norm_phrase = _normalize_phrase(phrase)
                if norm_phrase:
                    phrases.add(norm_phrase)
    return phrases


def _phrase_map_from_text_items(items: List[Dict[str, object]]) -> Dict[str, List[Dict[str, object]]]:
    phrase_map: Dict[str, List[Dict[str, object]]] = {}
    for item in items:
        text = item.get("text") or ""
        norm = _normalize_term(text)
        tokens = _tokenize(norm)
        for n in (1, 2, 3):
            for phrase in _ngram_tokens(tokens, n):
                norm_phrase = _normalize_phrase(phrase)
                if not norm_phrase or len(norm_phrase) < _MIN_MATCH_PHRASE_LEN or norm_phrase in get_match_stopwords():
                    continue
                meta = {k: v for k, v in item.items() if k != "text"}
                meta["matched_text"] = phrase
                phrase_map.setdefault(norm_phrase, []).append(meta)
    return phrase_map


_MATCH_KIND_PRIORITY: Dict[str, int] = {
    "pav_numeric": 90,
    "attr_value_label": 80,
    "pav_text_i18n": 70,
    "pav_text": 60,
    "attr_value_code": 55,
    "product_i18n_title": 40,
    "product_source_title": 35,
    "product_label": 30,
    "product_source_desc": 10,
    "product_i18n_desc": 10,
}


def _select_best_meta(items: List[Dict[str, object]]) -> Optional[Dict[str, object]]:
    if not items:
        return None
    return max(items, key=lambda item: _MATCH_KIND_PRIORITY.get(item.get("match_kind") or "", 0))


def _build_llm_instructions(
    focus_on: Optional[str] = None,
    ignore: Optional[str] = None,
    ignore_size_and_marketplace: bool = False,
    focus_head_terms: bool = False,
    focus_hook_terms: bool = False,
) -> str:
    base = (
        "Map each keyword to the product when it clearly refers to the product text or to ONE attribute. "
        "One attribute = one semantic dimension. Use semantic/synonym matching: e.g. 'flach'/'flat' → height/depth; "
        "'rot' → color; 'acryl'/'stahl' → material; 'a poser'/'encastrer' → installation. "
        "Do NOT mix dimensions: material and installation are separate; map each keyword to the attribute that matches its dimension only. "
        "Return JSON: {\"matches\":[{\"keyword_id\":<id>, \"reason\":\"short explanation\", \"attribute_code\":\"<code or null>\"}]}. "
        "Set attribute_code only when the keyword clearly describes that single attribute. Do not guess."
    )
    focus_parts: List[str] = []
    if focus_on and focus_on.strip():
        focus_parts.append(focus_on.strip())
    if focus_head_terms:
        focus_parts.append("head terms (broad category terms that describe the product type)")
    if focus_hook_terms:
        focus_parts.append("hook terms (specific, product-differentiating terms that uniquely describe this product)")
    if focus_parts:
        base += " Focus on: " + "; ".join(focus_parts)
    ignore_parts: List[str] = []
    if ignore and ignore.strip():
        ignore_parts.append(ignore.strip())
    if ignore_size_and_marketplace:
        ignore_parts.append(
            "size keywords (e.g. S, M, L, XL, dimensions in cm/mm), marketplace names (e.g. Amazon, eBay, Etsy)"
        )
    if ignore_parts:
        base += " Do NOT map keywords that are only: " + "; ".join(ignore_parts)
    return base


def product_keywords_for_run(
    *,
    product_id: int,
    run: PlannerRun,
    min_confidence: Optional[float] = None,
) -> QuerySet[AttributeMap]:
    """
    Virtual per-product mapping: return AttributeMap rows whose attribute_value_id
    exists on the product (or its variants) and whose keyword is in the run.
    """
    product_av_ids = ProductAttributeValue.objects.filter(
        Q(product_id=product_id) | Q(variant__product_id=product_id),
        attribute_value_id__isnull=False,
    ).values_list("attribute_value_id", flat=True)

    qs = (
        AttributeMap.objects.filter(
            attribute_value_id__in=product_av_ids,
            attribute_value_id__isnull=False,
            keyword__planner_runs__run=run,
        )
        .select_related("keyword", "attribute", "attribute_value")
        .annotate(vol=Max("keyword__metrics__avg_searches"))
        .order_by("-confidence", "-vol")
    )
    if min_confidence is not None:
        qs = qs.filter(confidence__gte=min_confidence)
    return qs


def product_keyword_matches_for_run(
    *,
    product_id: int,
    run: PlannerRun,
    min_confidence: Optional[float] = None,
    include_text_values: bool = True,
    include_i18n: bool = True,
    include_descriptions: bool = False,
    max_description_chars: Optional[int] = None,
    locale: Optional[Locale] = None,
    use_llm: bool = False,
    llm_max_keywords: int = 80,
    max_text_matches: Optional[int] = None,
    prk_list: Optional[List[PlannerRunKeyword]] = None,
    parse_map: Optional[Dict[int, List[str]]] = None,
    keyword_vol_map: Optional[Dict[int, int]] = None,
    focus_on: Optional[str] = None,
    ignore: Optional[str] = None,
    ignore_size_and_marketplace: bool = False,
    focus_head_terms: bool = False,
    focus_hook_terms: bool = False,
) -> Dict[str, object]:
    """
    Hybrid per-product mapping:
      - enum_maps: AttributeMap rows whose attribute_value_id exists on the product
      - text_matches: keywords whose phrases overlap product free-text values
    """
    # #region agent log
    try:
        _lp = _debug_log_path()
        os.makedirs(os.path.dirname(_lp), exist_ok=True)
        with open(_lp, "a") as _f:
            _f.write(json.dumps({"location": "product_keyword_mapper.py:matches_for_run:entry", "message": "product_keyword_matches_for_run entry", "data": {"product_id": product_id}, "hypothesisId": "H4", "timestamp": __import__("time").time() * 1000}) + "\n")
    except Exception:
        pass
    # #endregion
    enum_maps = product_keywords_for_run(
        product_id=product_id,
        run=run,
        min_confidence=min_confidence,
    )
    if ignore_size_and_marketplace:
        enum_maps = enum_maps.exclude(attribute__code__in=list(_SIZE_ATTRIBUTE_CODES))
    if not include_text_values:
        return {"enum_maps": enum_maps, "text_matches": []}
    if include_i18n and locale is None:
        locale = run.locale

    product = Product.objects.filter(id=product_id).first()
    # #region agent log
    try:
        with open(_debug_log_path(), "a") as _f:
            _f.write(json.dumps({"location": "product_keyword_mapper.py:matches_for_run:after_product", "message": "product fetched", "data": {"product_id": product_id, "has_product": product is not None}, "hypothesisId": "H4", "timestamp": __import__("time").time() * 1000}) + "\n")
    except Exception:
        pass
    # #endregion
    pav_qs = ProductAttributeValue.objects.filter(
        Q(product_id=product_id) | Q(variant__product_id=product_id)
    ).select_related("attribute", "attribute_value")
    text_values: List[str] = []
    text_items: List[Dict[str, object]] = []
    pav_by_id: Dict[int, ProductAttributeValue] = {}
    for pav in pav_qs:
        pav_by_id[pav.id] = pav
        if pav.value_text:
            text_values.append(pav.value_text)
            text_items.append(
                {
                    "text": pav.value_text,
                    "match_kind": "pav_text",
                    "attribute_id": pav.attribute_id,
                    "attribute_value_id": pav.attribute_value_id,
                    "product_attribute_value_id": pav.id,
                }
            )
        if pav.value_number is not None:
            text_values.append(str(pav.value_number))
            text_items.append(
                {
                    "text": str(pav.value_number),
                    "match_kind": "pav_numeric",
                    "attribute_id": pav.attribute_id,
                    "attribute_value_id": pav.attribute_value_id,
                    "product_attribute_value_id": pav.id,
                    "num_value": pav.value_number,
                    "num_unit": pav.unit,
                }
            )
            if pav.unit:
                text_values.append(f"{pav.value_number} {pav.unit}")
                text_values.append(f"{pav.value_number}{pav.unit}")
                text_items.extend(
                    [
                        {
                            "text": f"{pav.value_number} {pav.unit}",
                            "match_kind": "pav_numeric",
                            "attribute_id": pav.attribute_id,
                            "attribute_value_id": pav.attribute_value_id,
                            "product_attribute_value_id": pav.id,
                            "num_value": pav.value_number,
                            "num_unit": pav.unit,
                        },
                        {
                            "text": f"{pav.value_number}{pav.unit}",
                            "match_kind": "pav_numeric",
                            "attribute_id": pav.attribute_id,
                            "attribute_value_id": pav.attribute_value_id,
                            "product_attribute_value_id": pav.id,
                            "num_value": pav.value_number,
                            "num_unit": pav.unit,
                        },
                    ]
                )

    attribute_value_ids = {
        pav.attribute_value_id for pav in pav_by_id.values() if pav.attribute_value_id
    }
    if attribute_value_ids:
        av_qs = AttributeValue.objects.filter(id__in=attribute_value_ids).select_related("attribute")
        av_by_id = {av.id: av for av in av_qs}
        if include_i18n and locale:
            for av_i18n in AttributeValueI18n.objects.filter(
                attribute_value_id__in=attribute_value_ids,
                locale=locale,
            ):
                av = av_by_id.get(av_i18n.attribute_value_id)
                if not av or not av_i18n.label:
                    continue
                text_values.append(av_i18n.label)
                text_items.append(
                    {
                        "text": av_i18n.label,
                        "match_kind": "attr_value_label",
                        "attribute_id": av.attribute_id,
                        "attribute_value_id": av.id,
                    }
                )
        for av in av_by_id.values():
            if not av.code:
                continue
            text_values.append(av.code)
            text_items.append(
                {
                    "text": av.code,
                    "match_kind": "attr_value_code",
                    "attribute_id": av.attribute_id,
                    "attribute_value_id": av.id,
                }
            )
    if include_i18n and locale and pav_by_id:
        for pav_i18n in ProductAttributeValueI18n.objects.filter(
            product_attribute_value_id__in=list(pav_by_id.keys()),
            locale=locale,
        ).exclude(value_text=""):
            pav = pav_by_id.get(pav_i18n.product_attribute_value_id)
            if not pav or not pav_i18n.value_text:
                continue
            text_values.append(pav_i18n.value_text)
            text_items.append(
                {
                    "text": pav_i18n.value_text,
                    "match_kind": "pav_text_i18n",
                    "attribute_id": pav.attribute_id,
                    "attribute_value_id": pav.attribute_value_id,
                    "product_attribute_value_id": pav.id,
                }
            )
    if product:
        if product.default_label:
            text_values.append(product.default_label)
            text_items.append(
                {
                    "text": product.default_label,
                    "match_kind": "product_label",
                    "product_id": product.id,
                }
            )
        # Source fields are on Variant, not Product — match AI against each variant's title/description
        for variant in product.variants.all():
            if variant.source_title:
                text_values.append(variant.source_title)
                text_items.append(
                    {
                        "text": variant.source_title,
                        "match_kind": "product_source_title",
                        "product_id": product.id,
                        "variant_id": variant.id,
                    }
                )
            if variant.source_description and include_descriptions:
                desc = _normalize_whitespace(variant.source_description)
                if max_description_chars:
                    desc = desc[:max_description_chars]
                if desc:
                    text_values.append(desc)
                    text_items.append(
                        {
                            "text": desc,
                            "match_kind": "product_source_desc",
                            "product_id": product.id,
                            "variant_id": variant.id,
                        }
                    )
        if include_i18n and locale:
            prod_i18n = ProductI18n.objects.filter(product_id=product.id, locale=locale).first()
            if prod_i18n:
                if prod_i18n.title:
                    text_values.append(prod_i18n.title)
                    text_items.append(
                        {
                            "text": prod_i18n.title,
                            "match_kind": "product_i18n_title",
                            "product_id": product.id,
                        }
                    )
                if prod_i18n.description:
                    if include_descriptions:
                        desc = _normalize_whitespace(prod_i18n.description)
                        if max_description_chars:
                            desc = desc[:max_description_chars]
                        if desc:
                            text_values.append(desc)
                            text_items.append(
                                {
                                    "text": desc,
                                    "match_kind": "product_i18n_desc",
                                    "product_id": product.id,
                                }
                            )

    # Build attribute context for LLM: attribute code -> { sample_values, attribute_id }
    attribute_context: List[Dict[str, object]] = []
    code_to_attr_id: Dict[str, int] = {}
    attr_samples: Dict[int, List[str]] = {}
    for pav in pav_by_id.values():
        attr = pav.attribute
        code_to_attr_id[attr.code] = attr.id
        if attr.id not in attr_samples:
            attr_samples[attr.id] = []
        sample = None
        if pav.value_text:
            sample = pav.value_text.strip()[:80]
        elif pav.value_number is not None:
            sample = f"{pav.value_number}" + (f" {pav.unit}" if pav.unit else "")
        elif pav.attribute_value_id and pav.attribute_value:
            sample = (pav.attribute_value.code or getattr(pav.attribute_value, "label", None) or "")
        if sample and sample not in attr_samples[attr.id]:
            attr_samples[attr.id].append(sample)
    for code, attr_id in code_to_attr_id.items():
        attribute_context.append({
            "attribute_code": code,
            "attribute_id": attr_id,
            "sample_values": attr_samples.get(attr_id, [])[:10],
        })
    id_to_attr_code: Dict[int, str] = {aid: code for code, aid in code_to_attr_id.items()}

    product_phrase_map = _phrase_map_from_text_items(text_items)
    if not product_phrase_map:
        return {"enum_maps": enum_maps, "text_matches": []}

    if prk_list is None:
        prk_list = list(PlannerRunKeyword.objects.filter(run=run).select_related("keyword"))
    keyword_ids = [prk.keyword_id for prk in prk_list]
    if parse_map is None:
        parse_map = {}
        for row in (
            KeywordParse.objects.filter(keyword_id__in=keyword_ids)
            .values("keyword_id", "phrases")
            .order_by("keyword_id", "-updated_at")
        ):
            if row["keyword_id"] not in parse_map:
                parse_map[row["keyword_id"]] = list(row["phrases"] or [])

    text_matches: List[Dict[str, object]] = []
    matched_keyword_ids = set()
    for prk in prk_list:
        kw = prk.keyword
        phrases = parse_map.get(kw.id) or _phrases_from_term(kw.term or "")
        matched = None
        matched_meta: Optional[Dict[str, object]] = None
        for phrase in phrases:
            norm_phrase = _normalize_phrase(phrase)
            if not norm_phrase or len(norm_phrase) < _MIN_MATCH_PHRASE_LEN or norm_phrase in get_match_stopwords():
                continue
            if norm_phrase in product_phrase_map:
                matched = phrase
                matched_meta = _select_best_meta(product_phrase_map[norm_phrase])
                break
        norm_matched = _normalize_phrase(matched) if matched else ""
        if matched and len(norm_matched) >= _MIN_MATCH_PHRASE_LEN and norm_matched not in get_match_stopwords():
            attr_id = (matched_meta or {}).get("attribute_id")
            attr_code = id_to_attr_code.get(attr_id) if attr_id else None
            if ignore_size_and_marketplace and _is_size_attribute(attr_code):
                continue
            matched_keyword_ids.add(kw.id)
            text_matches.append(
                {
                    "keyword_id": kw.id,
                    "keyword": kw.term,
                    "matched_phrase": matched,
                    "source": (matched_meta or {}).get("match_kind") or "pav_text",
                    "match_kind": (matched_meta or {}).get("match_kind"),
                    "attribute_id": attr_id,
                    "attribute_value_id": (matched_meta or {}).get("attribute_value_id"),
                    "product_attribute_value_id": (matched_meta or {}).get("product_attribute_value_id"),
                    "num_value": (matched_meta or {}).get("num_value"),
                    "num_unit": (matched_meta or {}).get("num_unit"),
                    "matched_text": (matched_meta or {}).get("matched_text"),
                    "variant_id": (matched_meta or {}).get("variant_id"),
                }
            )

    if use_llm:
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                from openai import OpenAI
            except Exception:
                api_key = None
        if api_key:
            client = OpenAI(api_key=api_key)
            model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            remaining = [prk for prk in prk_list if prk.keyword_id not in matched_keyword_ids]
            remaining = remaining[: max(llm_max_keywords, 0)]
            keyword_items = [{"id": prk.keyword_id, "term": prk.keyword.term} for prk in remaining]
            text_snippet = " | ".join(text_values)[:2000]
            prompt = {
                "product_text_values": text_snippet,
                "attributes_on_product": attribute_context,
                "keywords": keyword_items,
                "locale": (locale.code if locale else ""),
                "instructions": _build_llm_instructions(
                    focus_on=focus_on,
                    ignore=ignore,
                    ignore_size_and_marketplace=ignore_size_and_marketplace,
                    focus_head_terms=focus_head_terms,
                    focus_hook_terms=focus_hook_terms,
                ),
            }
            try:
                resp = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You map search keywords to product attribute values or product text. "
                                "One attribute = one semantic dimension (e.g. material, installation, color, size). "
                                "Link each keyword to at most one attribute that matches its dimension: "
                                "material words (acrylic, steel) → material; installation words (surface-mounted, built-in) → installation; "
                                "do not mix dimensions in one mapping. Return valid JSON only."
                            ),
                        },
                        {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
                    ],
                    temperature=0,
                    max_tokens=400,
                    response_format={"type": "json_object"},
                )
                content = resp.choices[0].message.content or "{}"
                data = json.loads(content)
                for item in data.get("matches", []) or []:
                    kw_id = item.get("keyword_id")
                    if not kw_id or kw_id in matched_keyword_ids:
                        continue
                    kw_term = None
                    for prk in remaining:
                        if prk.keyword_id == kw_id:
                            kw_term = prk.keyword.term
                            break
                    if not kw_term:
                        continue
                    reason = (item.get("reason") or "").strip()
                    attr_code = (item.get("attribute_code") or "").strip() or None
                    if ignore_size_and_marketplace and _is_size_attribute(attr_code):
                        continue
                    matched_keyword_ids.add(kw_id)
                    attr_id = code_to_attr_id.get(attr_code) if attr_code else None
                    text_matches.append(
                        {
                            "keyword_id": kw_id,
                            "keyword": kw_term,
                            "matched_phrase": reason,
                            "source": "pav_text_llm",
                            "match_kind": "pav_text_llm",
                            "matched_text": reason,
                            "model": model_name,
                            "attribute_id": attr_id,
                            "attribute_code": attr_code,
                        }
                    )
            except Exception:
                pass

    def _text_match_sort_key(item: Dict[str, object]) -> tuple:
        priority = _MATCH_KIND_PRIORITY.get(item.get("match_kind") or "", 0)
        kw_id = int(item.get("keyword_id") or 0)
        volume = 0
        if keyword_vol_map is not None:
            volume = keyword_vol_map.get(kw_id, 0) or 0
        matched_phrase = item.get("matched_phrase") or ""
        return (-priority, -volume, len(matched_phrase), matched_phrase, kw_id)

    text_matches.sort(key=_text_match_sort_key)
    if max_text_matches:
        text_matches = text_matches[:max_text_matches]

    enum_maps_list = list(enum_maps)
    enum_maps_list = [
        am for am in enum_maps_list
        if not _numeric_substring_false_match(
            getattr(am.keyword, "term", "") or "",
            am.attribute_value.code if getattr(am, "attribute_value", None) else None,
        )
    ]
    return {"enum_maps": enum_maps_list, "text_matches": text_matches}


def persist_product_keyword_maps(
    run_id: int,
    *,
    product_id: Optional[int] = None,
    limit: Optional[int] = None,
    min_confidence: Optional[float] = None,
    include_text_values: bool = True,
    include_i18n: bool = True,
    include_descriptions: bool = False,
    max_description_chars: Optional[int] = 2000,
    max_text_matches: Optional[int] = 60,
    max_enum_maps: Optional[int] = 120,
    use_llm: bool = False,
    llm_max_keywords: int = 80,
    dry_run: bool = False,
    focus_on: Optional[str] = None,
    ignore: Optional[str] = None,
    ignore_size_and_marketplace: bool = False,
    focus_head_terms: bool = False,
    focus_hook_terms: bool = False,
) -> Dict[str, int]:
    """
    Persist per-product keyword mappings for a PlannerRun.
    
    Returns: {
        "products_processed": int,
        "maps_created": int,
        "maps_updated": int,
    }
    """
    # #region agent log
    try:
        with open(_debug_log_path(), "a") as _f:
            _f.write(json.dumps({"location": "product_keyword_mapper.py:persist:entry", "message": "persist_product_keyword_maps entry", "data": {"run_id": run_id, "product_id": product_id, "limit": limit}, "hypothesisId": "H1", "timestamp": __import__("time").time() * 1000}) + "\n")
    except Exception:
        pass
    # #endregion
    run = PlannerRun.objects.select_related("locale", "product_type").filter(id=run_id).first()
    if not run:
        raise ValueError(f"PlannerRun {run_id} not found")

    products = Product.objects.all()
    if run.product_type:
        products = products.filter(product_type=run.product_type)
    if product_id:
        products = products.filter(id=product_id)
    if limit:
        products = products[:limit]
    products_list = list(products)
    # #region agent log
    try:
        with open(_debug_log_path(), "a") as _f:
            _f.write(json.dumps({"location": "product_keyword_mapper.py:persist:products_count", "message": "products to process", "data": {"n": len(products_list)}, "hypothesisId": "H4", "timestamp": __import__("time").time() * 1000}) + "\n")
    except Exception:
        pass
    # #endregion

    prk_list = list(PlannerRunKeyword.objects.filter(run=run).select_related("keyword"))
    keyword_ids = [prk.keyword_id for prk in prk_list]
    
    parse_map: Dict[int, list] = {}
    for row in (
        KeywordParse.objects.filter(keyword_id__in=keyword_ids)
        .values("keyword_id", "phrases")
        .order_by("keyword_id", "-updated_at")
    ):
        if row["keyword_id"] not in parse_map:
            parse_map[row["keyword_id"]] = list(row["phrases"] or [])
    
    keyword_vol_map = {
        row["keyword_id"]: row["vol"] or 0
        for row in Metric.objects.filter(keyword_id__in=keyword_ids)
        .values("keyword_id")
        .annotate(vol=Max("avg_searches"))
    }

    if max_description_chars is not None and max_description_chars <= 0:
        max_description_chars = None
    if max_text_matches is not None and max_text_matches <= 0:
        max_text_matches = None
    if max_enum_maps is not None and max_enum_maps <= 0:
        max_enum_maps = None

    total = 0
    created = 0
    updated = 0

    for product in products_list:
        total += 1
        # #region agent log
        try:
            with open(_debug_log_path(), "a") as _f:
                _f.write(json.dumps({"location": "product_keyword_mapper.py:persist:loop_product", "message": "product iteration", "data": {"product_id": product.id, "total_so_far": total}, "hypothesisId": "H4,H5", "timestamp": __import__("time").time() * 1000}) + "\n")
        except Exception:
            pass
        # #endregion
        try:
            res = product_keyword_matches_for_run(
            product_id=product.id,
            run=run,
            min_confidence=min_confidence,
            include_text_values=include_text_values,
            include_i18n=include_i18n,
            include_descriptions=include_descriptions,
            max_description_chars=max_description_chars,
            use_llm=use_llm,
            llm_max_keywords=llm_max_keywords,
            max_text_matches=max_text_matches,
            prk_list=prk_list,
            parse_map=parse_map,
            keyword_vol_map=keyword_vol_map,
            focus_on=focus_on,
            ignore=ignore,
            ignore_size_and_marketplace=ignore_size_and_marketplace,
            focus_head_terms=focus_head_terms,
            focus_hook_terms=focus_hook_terms,
        )
        except Exception as _e:
            # #region agent log
            try:
                with open(_debug_log_path(), "a") as _f:
                    _f.write(json.dumps({"location": "product_keyword_mapper.py:persist:matches_raised", "message": "product_keyword_matches_for_run raised", "data": {"product_id": product.id, "exc_type": type(_e).__name__, "exc_msg": str(_e)[:400]}, "hypothesisId": "H4", "timestamp": __import__("time").time() * 1000}) + "\n")
            except Exception:
                pass
            # #endregion
            raise
        enum_maps_raw = res["enum_maps"]
        if max_enum_maps:
            enum_maps = list(enum_maps_raw)[:max_enum_maps]
        else:
            enum_maps = list(enum_maps_raw)
        text_matches = list(res["text_matches"])

        keyword_ids_for_text = {item["keyword_id"] for item in text_matches}
        keyword_map: Dict[int, Keyword] = {
            kw.id: kw for kw in Keyword.objects.filter(id__in=keyword_ids_for_text)
        }

        ctx = transaction.atomic() if not dry_run else nullcontext()
        try:
            with ctx:
                for amap in enum_maps:
                    if dry_run:
                        created += 1
                        continue
                    evidence_val = amap.evidence if isinstance(amap.evidence, dict) else {}
                    obj, is_created = ProductKeywordMap.objects.update_or_create(
                        product=product,
                        keyword=amap.keyword,
                        run=run,
                        source=ProductKeywordMap.Source.ENUM,
                        defaults={
                            "attribute": amap.attribute,
                            "attribute_value": amap.attribute_value,
                            "confidence": amap.confidence,
                            "match_kind": ProductKeywordMap.Source.ENUM.value,
                            "evidence": _json_safe({
                                "attribute_map_id": amap.id,
                                "reason_code": getattr(amap, "reason_code", "") or "",
                                "evidence": evidence_val,
                            }),
                        },
                    )
                    if is_created:
                        created += 1
                    else:
                        updated += 1

                for item in text_matches:
                    kw = keyword_map.get(item["keyword_id"])
                    if not kw:
                        continue
                    if dry_run:
                        created += 1
                        continue
                    raw_source = item.get("match_kind") or item.get("source") or ProductKeywordMap.Source.TEXT
                    valid_sources = {s.value for s in ProductKeywordMap.Source}
                    source = raw_source if isinstance(raw_source, str) and raw_source in valid_sources else ProductKeywordMap.Source.TEXT
                    if hasattr(source, "value"):
                        source = source.value
                    match_kind_raw = item.get("match_kind") or item.get("source") or ""
                    match_kind = str(match_kind_raw)[:32] if match_kind_raw else ""
                    num_val = item.get("num_value")
                    num_unit_val = item.get("num_unit")
                    if num_unit_val is not None and not isinstance(num_unit_val, str):
                        num_unit_val = str(num_unit_val)[:50]
                    obj, is_created = ProductKeywordMap.objects.update_or_create(
                        product=product,
                        keyword=kw,
                        run=run,
                        source=source,
                        defaults={
                            "confidence": None,
                            "attribute_id": item.get("attribute_id"),
                            "attribute_value_id": item.get("attribute_value_id"),
                            "num_value": num_val,
                            "num_unit": num_unit_val,
                            "match_kind": match_kind,
                            "matched_text": (item.get("matched_text") or "")[:65535],
                            "evidence": _json_safe({
                                "matched_phrase": item.get("matched_phrase"),
                                "model": item.get("model"),
                                "variant_id": item.get("variant_id"),
                            }),
                        },
                    )
                    if is_created:
                        created += 1
                    else:
                        updated += 1
        except Exception as _e:
            # #region agent log
            try:
                with open(_debug_log_path(), "a") as _f:
                    _f.write(json.dumps({"location": "product_keyword_mapper.py:persist:update_or_create_raised", "message": "update_or_create or atomic block raised", "data": {"product_id": product.id, "exc_type": type(_e).__name__, "exc_msg": str(_e)[:400]}, "hypothesisId": "H5", "timestamp": __import__("time").time() * 1000}) + "\n")
            except Exception:
                pass
            # #endregion
            raise
    return {
        "products_processed": total,
        "maps_created": created,
        "maps_updated": updated,
    }
