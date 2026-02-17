"""
Extract suggested head terms (product type) and hook terms (per product) from
ProductKeywordMap after mapping. Used so the user can approve/deny and save
for title generation.

Logic is language-agnostic: the same rules apply for every locale (head = general
product-type synonyms; hook = product-specific attributes). Terms are in the run's locale.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from django.db.models import Count, Max, Q

from catalog.models import Product, ProductAttributeValue, Variant
from content.models import AttributeI18n, ProductHookTerm, ProductTypeSynonym, SynonymStatus
from kw.models import Keyword, Metric, PlannerRun, ProductKeywordMap

# Match kinds that indicate general product-type synonyms (head terms): category, label, titles.
# We want only these for head terms—e.g. "Duschwanne", "Duschtasse", not colours or materials.
_HEAD_MATCH_KINDS = frozenset({
    "product_label", "product_category", "product_source_title", "product_i18n_title",
})
# Attribute-based match kinds: often colour, material, shape. Use for hook terms, not head.
_HEAD_ATTR_MATCH_KINDS = frozenset({"attr_value_label", "pav_text_i18n", "pav_text"})
# Allow attribute-based only as fallback when no product-type matches exist (ranked lower).
_HEAD_ALSO = _HEAD_ATTR_MATCH_KINDS

# Source values to exclude from hook suggestions (size/numeric-only).
_HOOK_EXCLUDE_SOURCE = frozenset({
    ProductKeywordMap.Source.ENUM.value,
    ProductKeywordMap.Source.NUMERIC.value,
    ProductKeywordMap.Source.ATTR_VALUE_CODE.value,
})

# Sense/priority for head terms: higher = prefer for head.
# Prefer general product-type sources (category, label, titles); attribute-based (colour, material) lower.
_HEAD_MATCH_KIND_ORDER = {
    "product_category": 90,
    "product_label": 85,
    "product_i18n_title": 80,
    "product_source_title": 75,
    "attr_value_label": 40,
    "pav_text_i18n": 35,
    "pav_text": 30,
}

# Priority for hook terms: prefer attribute-based over source title / product label.
_HOOK_MATCH_KIND_ORDER = {
    "attr_value_label": 90,
    "pav_text_i18n": 85,
    "pav_text": 80,
    "product_i18n_title": 50,
    "product_source_title": 45,
    "product_label": 40,
}


def _product_display(product_id: int) -> Dict[str, object]:
    """Return code, default_label, variant_sku, variant_source_title for a product (first variant)."""
    product = Product.objects.filter(id=product_id).only("code", "default_label").first()
    if not product:
        return {"code": None, "default_label": None, "variant_sku": None, "variant_source_title": None}
    variant = (
        Variant.objects.filter(product_id=product_id)
        .only("sku", "source_title")
        .order_by("id")
        .first()
    )
    return {
        "code": product.code or None,
        "default_label": (product.default_label or "").strip() or None,
        "variant_sku": (variant.sku or "").strip() or None if variant else None,
        "variant_source_title": (variant.source_title or "").strip() or None if variant else None,
    }


def extract_suggested_head_terms(
    run: PlannerRun,
    locale_id: int,
    channel_id: Optional[int] = None,
    max_terms: int = 20,
) -> List[Dict[str, object]]:
    """
    Suggest head terms for the run's product type from ProductKeywordMap.
    Only general product-type synonyms (e.g. Duschwanne, Duschtasse) are suggested—terms from
    product_label, product_category, product_source_title, product_i18n_title. Terms that come
    only from attribute values (colour, material, etc.) are excluded so head terms stay general.
    Exclude terms already in ProductTypeSynonym.
    """
    if not run.product_type_id:
        return []
    product_type = run.product_type
    existing = set(
        ProductTypeSynonym.objects.filter(
            product_type=product_type,
            locale_id=locale_id,
            status=SynonymStatus.APPROVED,
            is_active=True,
        )
        .filter(Q(channel_id=channel_id) | Q(channel__isnull=True))
        .values_list("term", flat=True)
    )
    # Normalize for comparison
    from kw.management.commands.parse_keywords import _normalize_term
    existing_norm = {_normalize_term(t) for t in existing if t}

    qs = (
        ProductKeywordMap.objects.filter(
            run=run,
            product__product_type_id=run.product_type_id,
        )
        .values("keyword_id", "match_kind", "product_id")
        .distinct()
    )
    by_kw: Dict[int, Dict[str, object]] = {}
    for row in qs:
        kw_id = row["keyword_id"]
        if kw_id not in by_kw:
            by_kw[kw_id] = {
                "keyword_id": kw_id,
                "product_ids": set(),
                "match_kinds": set(),
            }
        by_kw[kw_id]["product_ids"].add(row["product_id"])
        by_kw[kw_id]["match_kinds"].add(row["match_kind"] or "")
    for kw_id, data in by_kw.items():
        data["product_count"] = len(data["product_ids"])
        del data["product_ids"]

    # Fetch keyword terms
    keyword_ids = list(by_kw.keys())
    terms_by_id = dict(
        Keyword.objects.filter(id__in=keyword_ids).values_list("id", "term")
    )
    # Optional: search volume for ordering
    vol_by_id = dict(
        Metric.objects.filter(keyword_id__in=keyword_ids)
        .values("keyword_id")
        .annotate(vol=Max("avg_searches"))
        .values_list("keyword_id", "vol")
    )

    suggested = []
    for kw_id, data in by_kw.items():
        term = (terms_by_id.get(kw_id) or "").strip()
        if not term:
            continue
        norm = _normalize_term(term)
        if norm in existing_norm:
            continue
        match_kinds = data["match_kinds"]
        has_head = bool(match_kinds & _HEAD_MATCH_KINDS)
        has_also = bool(match_kinds & _HEAD_ALSO)
        if not (has_head or has_also):
            continue
        # Head terms must be general product-type synonyms (e.g. Duschwanne, Duschtasse).
        # Exclude terms that only come from attribute values (colour, material, etc.).
        if not has_head and has_also:
            continue
        product_count = data["product_count"]
        vol = vol_by_id.get(kw_id) or 0
        best_priority = max(
            (_HEAD_MATCH_KIND_ORDER.get(mk, 0) for mk in match_kinds),
            default=0,
        )
        pt = run.product_type
        suggested.append({
            "term": term,
            "keyword_id": kw_id,
            "product_count": product_count,
            "match_kinds": list(match_kinds),
            "avg_searches": int(vol),
            "product_type_id": run.product_type_id,
            "product_type_code": getattr(pt, "code", None) or None,
            "product_type_default_label": (getattr(pt, "default_label", None) or "").strip() or None,
            "product_type_notes": (getattr(pt, "notes", None) or "").strip() or None,
            "product_type_main_category": (getattr(pt, "main_category", None) or "").strip() or None,
            "_sense_priority": best_priority,
        })

    # Order by sense (match kind priority) then metrics (volume, product count) then term
    suggested.sort(
        key=lambda x: (
            -x["_sense_priority"],
            -x["avg_searches"],
            -x["product_count"],
            x["term"],
        ),
    )
    for x in suggested:
        del x["_sense_priority"]
    return suggested[:max_terms]


def extract_suggested_hook_terms(
    run: PlannerRun,
    product_id: int,
    locale_id: int,
    channel_id: Optional[int] = None,
    head_terms_normalized: Optional[set] = None,
    max_terms: int = 20,
) -> List[Dict[str, object]]:
    """
    Suggest hook terms for a product from its ProductKeywordMap rows.
    Prefer attribute-based match kinds over source title/product label. Exclude enum/numeric-only
    and terms already in ProductHookTerm for this product/locale/channel.
    """
    from kw.management.commands.parse_keywords import _normalize_term

    product = Product.objects.filter(id=product_id).first()
    if not product:
        return []
    # Attribute value IDs present on this product (product-level or any variant).
    product_av_ids = frozenset(
        ProductAttributeValue.objects.filter(
            Q(product_id=product_id) | Q(variant__product_id=product_id),
            attribute_value_id__isnull=False,
        ).values_list("attribute_value_id", flat=True)
    )
    existing = set(
        ProductHookTerm.objects.filter(
            product_id=product_id,
            locale_id=locale_id,
        )
        .filter(Q(channel_id=channel_id) | Q(channel__isnull=True))
        .values_list("term", flat=True)
    )
    existing_norm = {_normalize_term(t) for t in existing if t}
    head_norm = set(head_terms_normalized or [])

    qs = (
        ProductKeywordMap.objects.filter(
            run=run,
            product_id=product_id,
        )
        .exclude(source__in=_HOOK_EXCLUDE_SOURCE)
        .select_related("keyword", "attribute")
        .order_by("keyword_id", "-id")
    )
    seen_kw: Dict[int, Dict[str, object]] = {}
    for pkm in qs:
        # Only suggest terms whose mapped attribute value is on this product.
        # E.g. do not suggest "schwarz" for a product that is white.
        if pkm.attribute_value_id is not None and pkm.attribute_value_id not in product_av_ids:
            continue
        kw = pkm.keyword
        if not kw:
            continue
        term = (kw.term or "").strip()
        if not term:
            continue
        norm = _normalize_term(term)
        if norm in existing_norm or norm in head_norm:
            continue
        if pkm.source in _HOOK_EXCLUDE_SOURCE:
            continue
        if kw.id in seen_kw:
            continue
        attr = pkm.attribute
        seen_kw[kw.id] = {
            "term": term,
            "keyword_id": kw.id,
            "match_kind": pkm.match_kind or pkm.source,
            "source": pkm.source,
            "attribute_id": attr.id if attr else None,
            "attribute_code": attr.code if attr else None,
            "product_id": product_id,
        }

    suggested = list(seen_kw.values())
    attr_ids = list({s["attribute_id"] for s in suggested if s.get("attribute_id")})
    attr_labels = {}
    if attr_ids and locale_id:
        attr_labels = dict(
            AttributeI18n.objects.filter(
                attribute_id__in=attr_ids,
                locale_id=locale_id,
            ).values_list("attribute_id", "label")
        )
    for s in suggested:
        aid = s.get("attribute_id")
        s["attribute_label"] = (attr_labels.get(aid) or "").strip() or None if aid else None

    keyword_ids = [s["keyword_id"] for s in suggested]
    vol_by_id = dict(
        Metric.objects.filter(keyword_id__in=keyword_ids)
        .values("keyword_id")
        .annotate(vol=Max("avg_searches"))
        .values_list("keyword_id", "vol")
    )
    for s in suggested:
        s["avg_searches"] = int(vol_by_id.get(s["keyword_id"]) or 0)
        s["_sense_priority"] = _HOOK_MATCH_KIND_ORDER.get(s["match_kind"], 0)
    # Order by sense (attribute-based first) then metrics then term
    suggested.sort(key=lambda x: (-x["_sense_priority"], -x["avg_searches"], x["term"]))
    for s in suggested:
        del s["_sense_priority"]
    suggested = suggested[:max_terms]
    # Attach product display (SKU or source title) for each
    product_display = _product_display(product_id)
    for s in suggested:
        s["product_display"] = product_display
    return suggested


def generate_head_term_meanings_en(
    suggested_head: List[Dict[str, object]],
    product_type_label: Optional[str] = None,
    product_type_code: Optional[str] = None,
) -> List[Optional[str]]:
    """
    Use AI (OpenAI) to generate a short English meaning for each suggested head term.
    Returns a list of meaning_en in the same order as suggested_head; None or empty on failure.
    """
    import json
    import os

    if not suggested_head:
        return []
    terms_to_send = []
    indices = []  # index in suggested_head for each term we send
    for i, h in enumerate(suggested_head):
        t = (h.get("term") or "").strip()
        if t:
            terms_to_send.append(t)
            indices.append(i)
    if not terms_to_send:
        return [None] * len(suggested_head)

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return [None] * len(suggested_head)
    try:
        from openai import OpenAI
    except Exception:
        return [None] * len(suggested_head)

    model_name = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    context = product_type_label or product_type_code or "product category"
    if product_type_code and product_type_label:
        context = f"{product_type_label} ({product_type_code})"
    elif product_type_code:
        context = product_type_code

    prompt = (
        f"Product type / category: {context}\n\n"
        "Below are search terms (keywords) in another language for this product type. "
        "For each term, provide a short English meaning or description (one phrase, e.g. 'shower sliding door', '90x90 shower tray'). "
        "Keep it brief and useful for a catalog manager.\n\n"
        "Terms (one per line):\n"
        + "\n".join(terms_to_send)
        + "\n\n"
        "Return valid JSON only: {\"meanings\": [\"meaning1\", \"meaning2\", ...]} in the same order as the terms."
    )
    try:
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": "You provide short English meanings for product search terms. Return valid JSON only with a 'meanings' array of strings, one per term, in the same order.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=800,
        )
        content = (resp.choices[0].message.content or "").strip()
        data = json.loads(content)
        raw = data.get("meanings") or []
        if not isinstance(raw, list):
            return [None] * len(suggested_head)
        out = [None] * len(suggested_head)
        for pos, idx in enumerate(indices):
            if pos < len(raw) and idx < len(out):
                val = raw[pos]
                out[idx] = (val or "").strip() or None if isinstance(val, str) else None
        return out
    except Exception:
        pass
    return [None] * len(suggested_head)
