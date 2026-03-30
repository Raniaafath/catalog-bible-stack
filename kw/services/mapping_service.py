"""Run keyword-to-attribute mapping (rules-based) for a PlannerRun."""

from __future__ import annotations

import re
from contextlib import nullcontext
from typing import List


def _numeric_substring_false_match(phrase: str, key_term: str) -> bool:
    """
    Return True if this contains-match is likely wrong: key_term is numeric and
    appears as a strict substring of a longer number in the phrase.
    E.g. key_term="40" inside phrase "140" → True (false positive).
    """
    if not key_term or not key_term.strip().isdigit():
        return False
    val = key_term.strip()
    num_tokens = re.findall(r"\d+", phrase)
    for token in num_tokens:
        if token != val and val in token:
            return True
    return False


def _contains_confidence(phrase: str, key_term: str) -> float:
    """
    Score a contains-match by how specific the key_term is relative to the phrase.
    Longer key_terms matched inside a phrase are more reliable than very short ones.
    Score ranges 0.45–0.75 (always below exact match's 1.0).
    """
    p_len = len(phrase.strip())
    k_len = len(key_term.strip())
    if p_len == 0:
        return 0.6
    ratio = min(k_len / p_len, 1.0)
    # Base 0.45 + up to 0.3 bonus for ratio
    return round(0.45 + ratio * 0.30, 2)


from django.db import transaction

from catalog.models import AttributeValue
from kw.models import AttributeMap, KeywordParse, PlannerRun, PlannerRunKeyword
from kw.services.seed_builder import TITLE_ELIGIBLE_ATTRS_BY_PT

# Reuse helpers from the management command
from kw.management.commands.map_keywords import (
    _get_run_value_universe,
    _lexicon_for_values,
    _phrases_from_term,
)


def run_rules_mapping(
    run_id: int,
    *,
    limit: int | None = 500,
    dry_run: bool = False,
) -> dict:
    """
    Run rules-based keyword mapping for the given PlannerRun.
    Returns {"mapped": int, "mapping_ids": list[int]} (mapping_ids empty when dry_run).
    """
    run = (
        PlannerRun.objects.select_related("locale", "channel", "product_type")
        .filter(id=run_id)
        .first()
    )
    if not run:
        return {"mapped": 0, "mapping_ids": [], "error": "PlannerRun not found"}

    allowed_av_ids = _get_run_value_universe(run)
    if run.product_type and run.product_type.code in TITLE_ELIGIBLE_ATTRS_BY_PT:
        allowed_attr_codes = set(TITLE_ELIGIBLE_ATTRS_BY_PT.get(run.product_type.code, []))
        if not allowed_attr_codes:
            return {"mapped": 0, "mapping_ids": [], "error": "No title-eligible attributes for this product type"}
    else:
        allowed_attr_codes = None

    if allowed_av_ids is not None and allowed_attr_codes:
        allowed_av_ids = set(
            AttributeValue.objects.filter(
                id__in=allowed_av_ids,
                attribute__code__in=allowed_attr_codes,
            ).values_list("id", flat=True)
        )

    lexicon = _lexicon_for_values(
        locale=run.locale,
        channel=run.channel,
        allowed_av_ids=allowed_av_ids,
    )
    if not lexicon:
        return {"mapped": 0, "mapping_ids": [], "error": "Lexicon empty for this scope"}

    prk_qs = PlannerRunKeyword.objects.filter(run=run).select_related("keyword")
    if limit:
        prk_qs = prk_qs[:limit]

    mapping_ids: List[int] = []
    mapped = 0
    ctx = transaction.atomic() if not dry_run else nullcontext()
    with ctx:
        for prk in prk_qs:
            kw = prk.keyword
            phrases = []
            parse = KeywordParse.objects.filter(keyword=kw).order_by("-updated_at").first()
            if parse and parse.phrases:
                phrases = list(parse.phrases)
            else:
                phrases = _phrases_from_term(kw.term or "")

            seen = set()
            for phrase in phrases:
                p_norm = re.sub(r"\s+", " ", (phrase or "").strip().lower())
                if not p_norm or p_norm in seen:
                    continue
                seen.add(p_norm)
                match_type = None
                matched_term = None
                match = lexicon.get(p_norm)
                if match:
                    match_type = "exact"
                    matched_term = p_norm
                else:
                    for key_term, pair in lexicon.items():
                        if key_term != p_norm and key_term in p_norm:
                            if _numeric_substring_false_match(p_norm, key_term):
                                continue
                            match = pair
                            match_type = "contains"
                            matched_term = key_term
                            break
                if not match:
                    continue
                attr, aval = match
                if match_type == "exact":
                    conf = 1.0
                else:
                    conf = _contains_confidence(p_norm, matched_term or "")
                if dry_run:
                    mapped += 1
                    continue
                obj, _ = AttributeMap.objects.update_or_create(
                    keyword=kw,
                    attribute=attr,
                    attribute_value=aval,
                    defaults={
                        "confidence": conf,
                        "status": AttributeMap.Status.SUGGESTED,
                        "tagged_by": "rules",
                        "origin_run_keyword": prk,
                        "reason": "lexicon_match",
                        "reason_code": f"lexicon_{match_type}" if match_type else "lexicon",
                        "evidence": {
                            "matched_phrase": phrase,
                            "lexicon_term": matched_term,
                            "source": "parse" if parse and parse.phrases else "tokenize",
                        },
                    },
                )
                mapping_ids.append(obj.id)
                mapped += 1

    return {"mapped": mapped, "mapping_ids": mapping_ids}
