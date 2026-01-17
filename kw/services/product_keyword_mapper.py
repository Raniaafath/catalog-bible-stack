from __future__ import annotations

import json
import os
import re
from typing import Dict, List, Optional

from django.db.models import Max, Q, QuerySet

from catalog.models import AttributeValue, Product, ProductAttributeValue
from content.models import AttributeValueI18n, Locale, ProductAttributeValueI18n, ProductI18n
from kw.management.commands.parse_keywords import _normalize_term, _ngram_tokens, _tokenize
from kw.models import AttributeMap, KeywordParse, PlannerRun, PlannerRunKeyword

_SPACE_RE = re.compile(r"\s+")


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
                if not norm_phrase:
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
) -> Dict[str, object]:
    """
    Hybrid per-product mapping:
      - enum_maps: AttributeMap rows whose attribute_value_id exists on the product
      - text_matches: keywords whose phrases overlap product free-text values
    """
    enum_maps = product_keywords_for_run(
        product_id=product_id,
        run=run,
        min_confidence=min_confidence,
    )
    if not include_text_values:
        return {"enum_maps": enum_maps, "text_matches": []}
    if include_i18n and locale is None:
        locale = run.locale

    product = Product.objects.filter(id=product_id).first()
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
        if product.source_title:
            text_values.append(product.source_title)
            text_items.append(
                {
                    "text": product.source_title,
                    "match_kind": "product_source_title",
                    "product_id": product.id,
                }
            )
        if product.source_description:
            if include_descriptions:
                desc = _normalize_whitespace(product.source_description)
                if max_description_chars:
                    desc = desc[:max_description_chars]
                if desc:
                    text_values.append(desc)
                    text_items.append(
                        {
                            "text": desc,
                            "match_kind": "product_source_desc",
                            "product_id": product.id,
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
            if norm_phrase and norm_phrase in product_phrase_map:
                matched = phrase
                matched_meta = _select_best_meta(product_phrase_map[norm_phrase])
                break
        if matched:
            matched_keyword_ids.add(kw.id)
            text_matches.append(
                {
                    "keyword_id": kw.id,
                    "keyword": kw.term,
                    "matched_phrase": matched,
                    "source": (matched_meta or {}).get("match_kind") or "pav_text",
                    "match_kind": (matched_meta or {}).get("match_kind"),
                    "attribute_id": (matched_meta or {}).get("attribute_id"),
                    "attribute_value_id": (matched_meta or {}).get("attribute_value_id"),
                    "product_attribute_value_id": (matched_meta or {}).get("product_attribute_value_id"),
                    "num_value": (matched_meta or {}).get("num_value"),
                    "num_unit": (matched_meta or {}).get("num_unit"),
                    "matched_text": (matched_meta or {}).get("matched_text"),
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
                "keywords": keyword_items,
                "locale": (locale.code if locale else ""),
                "instructions": (
                    "Return JSON {\"matches\":[{\"keyword_id\":<id>,\"reason\":\"...\"}]} "
                    "for keywords that refer to the product text values, including synonyms or paraphrases. "
                    "Do not guess."
                ),
            }
            try:
                resp = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "You map keywords to product attribute text values."},
                        {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
                    ],
                    temperature=0,
                    max_tokens=300,
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
                    matched_keyword_ids.add(kw_id)
                    text_matches.append(
                        {
                            "keyword_id": kw_id,
                            "keyword": kw_term,
                            "matched_phrase": (item.get("reason") or "").strip(),
                            "source": "pav_text_llm",
                            "match_kind": "pav_text_llm",
                            "matched_text": (item.get("reason") or "").strip(),
                            "model": model_name,
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

    return {"enum_maps": enum_maps, "text_matches": text_matches}
