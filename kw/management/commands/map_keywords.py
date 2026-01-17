from __future__ import annotations

import re
import os
import json
from collections import Counter
from contextlib import nullcontext
from typing import Dict, List, Optional, Tuple

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q, Max, Count

from catalog.models import Attribute, AttributeValue, Product, ProductAttributeValue
from content.models import Locale, ProductI18n
from kw.management.commands.parse_keywords import _normalize_term, _tokenize, _ngram_tokens
from kw.models import AttributeMap, KeywordParse, PlannerRun, PlannerRunKeyword
from kw.services.seed_builder import TITLE_ELIGIBLE_ATTRS_BY_PT
from content.models import AttributeValueSynonym, AttributeValueI18n, Channel  # type: ignore
from django.conf import settings


def _get_run_value_universe(run: PlannerRun) -> Optional[set[int]]:
    if not run.product_type:
        return None
    pav_ids = (
        ProductAttributeValue.objects.filter(attribute_value_id__isnull=False)
        .filter(Q(product__product_type=run.product_type) | Q(variant__product__product_type=run.product_type))
        .values_list("attribute_value_id", flat=True)
        .distinct()
    )
    return set(pav_ids)


def _lexicon_for_values(
    *,
    locale: Locale,
    channel: Optional[Channel],
    allowed_av_ids: Optional[set[int]],
) -> Dict[str, Tuple[Attribute, AttributeValue]]:
    """
    Build a normalized term -> (attribute, attribute_value) lexicon from approved synonyms first,
    then i18n labels.
    """
    def norm(s: str) -> str:
        return re.sub(r"\s+", " ", s.strip().lower())

    lex: Dict[str, Tuple[Attribute, AttributeValue]] = {}

    syn_qs = (
        AttributeValueSynonym.objects.filter(
            locale=locale,
            status=AttributeValueSynonym.Status.APPROVED,
        )
        .filter(Q(channel=channel) | Q(channel__isnull=True))
        .select_related("attribute_value", "attribute_value__attribute")
        .order_by("-channel", "-score", "-updated_at")
    )
    if allowed_av_ids is not None:
        syn_qs = syn_qs.filter(attribute_value_id__in=allowed_av_ids)

    for syn in syn_qs:
        key = norm(syn.term)
        if not key or key in lex:
            continue
        lex[key] = (syn.attribute_value.attribute, syn.attribute_value)

    i18n_qs = (
        AttributeValueI18n.objects.filter(locale=locale)
        .select_related("attribute_value", "attribute_value__attribute")
        .order_by("attribute_value_id")
    )
    if allowed_av_ids is not None:
        i18n_qs = i18n_qs.filter(attribute_value_id__in=allowed_av_ids)

    for lbl in i18n_qs:
        key = norm(lbl.label)
        if not key or key in lex:
            continue
        lex[key] = (lbl.attribute_value.attribute, lbl.attribute_value)

    av_qs = AttributeValue.objects.select_related("attribute")
    if allowed_av_ids is not None:
        av_qs = av_qs.filter(id__in=allowed_av_ids)
    for av in av_qs:
        key = norm(av.code)
        if not key or key in lex:
            continue
        lex[key] = (av.attribute, av)

    return lex


def _phrases_from_term(term: str) -> list[str]:
    norm = _normalize_term(term)
    tokens = _tokenize(norm)
    phrases: list[str] = []
    for n in (1, 2, 3):
        phrases.extend(list(_ngram_tokens(tokens, n)))
    return phrases


def _lang_prefix(code: Optional[str]) -> str:
    if not code:
        return ""
    return code.split("-")[0].strip().lower()


_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    cleaned = _TAG_RE.sub(" ", text)
    return re.sub(r"\s+", " ", cleaned).strip()


def _product_description_terms(
    *,
    run: PlannerRun,
    max_products: int = 200,
    max_terms: int = 120,
    max_ngram: int = 3,
    min_df: int = 2,
    max_df_ratio: float = 0.6,
    ignore_source_locale: bool = False,
) -> Tuple[List[str], dict]:
    if not run.product_type:
        return [], {
            "source": None,
            "i18n_rows_sampled": 0,
            "source_rows_sampled": 0,
            "docs_used": 0,
            "terms_total": 0,
            "terms_returned": 0,
        }

    phrases: Counter[str] = Counter()
    doc_freq: Counter[str] = Counter()
    target_lang = _lang_prefix(run.locale.code if run.locale else "")

    i18n_rows = list(
        ProductI18n.objects.filter(product__product_type=run.product_type, locale=run.locale)
        .values_list("title", "description")[:max_products]
    )
    rows = [(title, desc, None) for title, desc in i18n_rows]
    remaining = max(0, max_products - len(i18n_rows))
    source_rows = []
    if remaining:
        source_rows = list(
            Product.objects.filter(product_type=run.product_type)
            .values_list("source_title", "source_description", "source_locale")[:remaining]
        )
    rows.extend(source_rows)

    doc_count = 0
    for title, desc, src_locale in rows:
        if not ignore_source_locale and src_locale and target_lang:
            if _lang_prefix(src_locale) != target_lang:
                continue
        doc_count += 1
        doc_terms = set()
        for text in (title or "", desc or ""):
            text = _strip_html(text)
            tokens = [t for t in _tokenize(text) if t and not t.isdigit() and len(t) >= 2]
            for n in range(1, max_ngram + 1):
                for phrase in _ngram_tokens(tokens, n):
                    phrases[phrase] += 1
                    doc_terms.add(phrase)
        for phrase in doc_terms:
            doc_freq[phrase] += 1

    if not phrases:
        return [], {
            "source": "i18n+source",
            "i18n_rows_sampled": len(i18n_rows),
            "source_rows_sampled": len(source_rows),
            "docs_used": doc_count,
            "terms_total": 0,
            "terms_returned": 0,
        }

    filtered: List[tuple[str, int]] = []
    for term, freq in phrases.items():
        df = doc_freq.get(term, 0)
        if df < min_df:
            continue
        if doc_count and (df / doc_count) > max_df_ratio:
            continue
        filtered.append((term, freq))

    filtered.sort(key=lambda x: x[1], reverse=True)
    terms = [term for term, _ in filtered[:max_terms]]
    stats = {
        "source": "i18n+source",
        "i18n_rows_sampled": len(i18n_rows),
        "source_rows_sampled": len(source_rows),
        "docs_used": doc_count,
        "terms_total": len(filtered),
        "terms_returned": len(terms),
    }
    return terms, stats


def _candidate_terms_for_value(av: AttributeValue, locale: Locale, channel: Optional[Channel]) -> List[str]:
    terms: List[str] = []
    seen = set()

    def add_term(term: Optional[str]) -> None:
        if not term:
            return
        key = re.sub(r"\s+", " ", term.strip().lower())
        if not key or key in seen:
            return
        seen.add(key)
        terms.append(term)
    syn_qs = AttributeValueSynonym.objects.filter(
        attribute_value=av,
        locale=locale,
        status=AttributeValueSynonym.Status.APPROVED,
    ).filter(Q(channel=channel) | Q(channel__isnull=True))
    for syn in syn_qs:
        add_term(syn.term)
    lbl = (
        AttributeValueI18n.objects.filter(attribute_value=av, locale=locale)
        .values_list("label", flat=True)
        .first()
    )
    if lbl:
        add_term(lbl)
    add_term(av.code)
    return terms


def _report_coverage(
    *,
    allowed_av_ids: Optional[set[int]],
    locale: Locale,
    channel: Optional[Channel],
    stdout,
) -> None:
    if allowed_av_ids is None:
        return
    if not allowed_av_ids:
        stdout.write("Coverage report: no attribute values found for this product type.")
        return

    syn_av_ids = set(
        AttributeValueSynonym.objects.filter(
            locale=locale,
            status=AttributeValueSynonym.Status.APPROVED,
        )
        .filter(Q(channel=channel) | Q(channel__isnull=True))
        .filter(attribute_value_id__in=allowed_av_ids)
        .values_list("attribute_value_id", flat=True)
        .distinct()
    )
    i18n_av_ids = set(
        AttributeValueI18n.objects.filter(locale=locale)
        .filter(attribute_value_id__in=allowed_av_ids)
        .values_list("attribute_value_id", flat=True)
        .distinct()
    )
    missing = allowed_av_ids - syn_av_ids - i18n_av_ids

    stdout.write(
        "Coverage report: "
        f"used_values={len(allowed_av_ids)} "
        f"with_synonyms={len(syn_av_ids)} "
        f"with_i18n={len(i18n_av_ids)} "
        f"missing_labels={len(missing)}"
    )
    if not missing:
        return

    counts = (
        AttributeValue.objects.filter(id__in=missing)
        .values("attribute__code")
        .annotate(count=Count("id"))
        .order_by("-count", "attribute__code")
    )
    top = (
        AttributeValue.objects.filter(id__in=missing)
        .values_list("id", "code", "attribute__code")
        .order_by("attribute__code", "code")[:10]
    )
    counts_str = ", ".join([f"{row['attribute__code']}={row['count']}" for row in counts[:8]])
    stdout.write(f"Coverage missing by attribute: {counts_str or 'n/a'}")
    top_str = ", ".join([f"{av_id}:{attr_code}:{code}" for av_id, code, attr_code in top])
    stdout.write(f"Coverage missing examples: {top_str or 'n/a'}")


def _score_overlap(phrases: List[str], candidate_terms: List[str]) -> int:
    norm_phrases = {re.sub(r"\s+", " ", p.strip().lower()) for p in phrases if p}
    score = 0
    for term in candidate_terms:
        norm = re.sub(r"\s+", " ", term.strip().lower())
        if norm in norm_phrases:
            score += 2
        else:
            for p in norm_phrases:
                if norm in p or p in norm:
                    score += 1
                    break
    return score


def _build_shortlist(
    *,
    locale: Locale,
    channel: Optional[Channel],
    allowed_attr_codes: Optional[set[str]],
    allowed_av_ids: Optional[set[int]] = None,
    per_attr_limit: int = 20,
) -> Dict[int, Dict[str, object]]:
    """
    Build a shortlist of attribute values per attribute id.
    Returns {attribute_id: {"code": attr_code, "values": [{"id": aval.id, "label": str}, ...]}}
    """
    shortlist: Dict[int, Dict[str, object]] = {}

    def add(attr: Attribute, aval: AttributeValue, label: str):
        if allowed_attr_codes and attr.code not in allowed_attr_codes:
            return
        slot = shortlist.setdefault(
            attr.id,
            {"code": attr.code, "values": []},
        )
        if len(slot["values"]) >= per_attr_limit:
            return
        slot["values"].append({"id": aval.id, "label": label})

    syn_qs = (
        AttributeValueSynonym.objects.filter(
            locale=locale,
            status=AttributeValueSynonym.Status.APPROVED,
        )
        .filter(Q(channel=channel) | Q(channel__isnull=True))
        .select_related("attribute_value", "attribute_value__attribute")
        .order_by("-channel", "-score", "-updated_at")
    )
    if allowed_av_ids is not None:
        syn_qs = syn_qs.filter(attribute_value_id__in=allowed_av_ids)
    if allowed_attr_codes:
        syn_qs = syn_qs.filter(attribute_value__attribute__code__in=allowed_attr_codes)

    for syn in syn_qs:
        add(syn.attribute_value.attribute, syn.attribute_value, syn.term)

    i18n_qs = (
        AttributeValueI18n.objects.filter(locale=locale)
        .select_related("attribute_value", "attribute_value__attribute")
        .order_by("attribute_value_id")
    )
    if allowed_av_ids is not None:
        i18n_qs = i18n_qs.filter(attribute_value_id__in=allowed_av_ids)
    if allowed_attr_codes:
        i18n_qs = i18n_qs.filter(attribute_value__attribute__code__in=allowed_attr_codes)

    for lbl in i18n_qs:
        add(lbl.attribute_value.attribute, lbl.attribute_value, lbl.label)

    return shortlist


class Command(BaseCommand):
    help = (
        "Map keywords to AttributeMap using rule-based lexicon or AI.\n"
        "Usage: map_keywords --run <id> --mode rules|ai [--limit N] [--dry-run]"
    )

    def add_arguments(self, parser):
        parser.add_argument("--run", type=int, required=True, help="PlannerRun id to map keywords from.")
        parser.add_argument("--mode", choices=["rules", "ai"], default="rules", help="Mapping mode.")
        parser.add_argument("--limit", type=int, default=None, help="Optional limit of keywords to map.")
        parser.add_argument("--dry-run", action="store_true", help="Do not write to DB.")
        parser.add_argument(
            "--intent-gate",
            action="store_true",
            help="Use an LLM intent gate to skip non-product keywords.",
        )
        parser.add_argument(
            "--intent-threshold",
            type=float,
            default=0.75,
            help="Confidence threshold for intent gating (default 0.75).",
        )
        parser.add_argument(
            "--no-rules-first",
            action="store_true",
            help="Skip running rules mapping before AI when --mode=ai.",
        )
        parser.add_argument(
            "--no-fallback-rules",
            action="store_true",
            help="Disable rules fallback when AI is unavailable.",
        )
        parser.add_argument(
            "--context-max-products",
            type=int,
            default=200,
            help="Max products to sample for AI context terms (default 200).",
        )
        parser.add_argument(
            "--context-max-terms",
            type=int,
            default=120,
            help="Max context terms to pass to the AI (default 120).",
        )
        parser.add_argument(
            "--context-max-ngram",
            type=int,
            default=3,
            help="Max n-gram size for context terms (default 3).",
        )
        parser.add_argument(
            "--context-min-df",
            type=int,
            default=2,
            help="Minimum document frequency for context terms (default 2).",
        )
        parser.add_argument(
            "--context-max-df-ratio",
            type=float,
            default=0.6,
            help="Drop context terms appearing in more than this ratio of docs (default 0.6).",
        )
        parser.add_argument(
            "--context-debug",
            action="store_true",
            help="Log product context term stats for AI mapping.",
        )
        parser.add_argument(
            "--context-respect-source-locale",
            action="store_true",
            help="Respect source_locale when sampling Product source descriptions (default: ignore).",
        )
        parser.add_argument(
            "--coverage-report",
            action="store_true",
            help="Report missing i18n/synonyms for product-used attribute values.",
        )

    def handle(self, *args, **opts):
        run_id = opts["run"]
        mode = opts["mode"]
        limit = opts["limit"]
        dry = opts["dry_run"]
        intent_gate = opts["intent_gate"]
        intent_threshold = opts["intent_threshold"]
        rules_first = not opts["no_rules_first"]
        fallback_rules = not opts["no_fallback_rules"]
        context_max_products = opts["context_max_products"]
        context_max_terms = opts["context_max_terms"]
        context_max_ngram = opts["context_max_ngram"]
        context_min_df = opts["context_min_df"]
        context_max_df_ratio = opts["context_max_df_ratio"]
        context_debug = opts["context_debug"]
        context_ignore_source_locale = not opts["context_respect_source_locale"]
        coverage_report = opts["coverage_report"]

        run = PlannerRun.objects.select_related("locale", "channel", "product_type").filter(id=run_id).first()
        if not run:
            raise CommandError(f"PlannerRun {run_id} not found")

        allowed_av_ids = _get_run_value_universe(run)
        if run.product_type and run.product_type.code in TITLE_ELIGIBLE_ATTRS_BY_PT:
            allowed_attr_codes = set(TITLE_ELIGIBLE_ATTRS_BY_PT.get(run.product_type.code, []))
            if not allowed_attr_codes:
                self.stdout.write(self.style.WARNING("No title-eligible attributes configured for this product type."))
                return
        else:
            allowed_attr_codes = None

        if allowed_av_ids is not None and allowed_attr_codes:
            allowed_av_ids = set(
                AttributeValue.objects.filter(
                    id__in=allowed_av_ids,
                    attribute__code__in=allowed_attr_codes,
                ).values_list("id", flat=True)
            )

        if coverage_report:
            _report_coverage(
                allowed_av_ids=allowed_av_ids,
                locale=run.locale,
                channel=run.channel,
                stdout=self.stdout,
            )
        if mode == "rules":
            prk_qs = PlannerRunKeyword.objects.filter(run=run).select_related("keyword")
            if limit:
                prk_qs = prk_qs[:limit]
            if not prk_qs.exists():
                raise CommandError(f"No PlannerRunKeyword found for run {run_id}")
            lexicon = _lexicon_for_values(
                locale=run.locale,
                channel=run.channel,
                allowed_av_ids=allowed_av_ids,
            )
            if not lexicon:
                self.stdout.write(self.style.WARNING("Lexicon is empty for this scope; nothing to map."))
                return
            mapped = self._map_rules(
                prk_qs,
                run,
                lexicon,
                dry=dry,
                intent_gate=intent_gate,
                intent_threshold=intent_threshold,
            )
            self.stdout.write(
                self.style.SUCCESS(f"Mapped keywords for run {run_id} (mode=rules): {mapped} mappings{' (dry-run)' if dry else ''}")
            )
            return

        if mode == "ai":
            mapped = 0
            if rules_first:
                prk_qs = PlannerRunKeyword.objects.filter(run=run).select_related("keyword")
                if limit:
                    prk_qs = prk_qs[:limit]
                lexicon = _lexicon_for_values(
                    locale=run.locale,
                    channel=run.channel,
                    allowed_av_ids=allowed_av_ids,
                )
                if lexicon:
                    mapped += self._map_rules(
                        prk_qs,
                        run,
                        lexicon,
                        dry=dry,
                        intent_gate=intent_gate,
                        intent_threshold=intent_threshold,
                    )
            mapped_ai = self._map_ai(
                run=run,
                limit=limit,
                dry=dry,
                intent_gate=intent_gate,
                intent_threshold=intent_threshold,
                fallback_rules=fallback_rules,
                context_max_products=context_max_products,
                context_max_terms=context_max_terms,
                context_max_ngram=context_max_ngram,
                context_min_df=context_min_df,
                context_max_df_ratio=context_max_df_ratio,
                context_debug=context_debug,
                context_ignore_source_locale=context_ignore_source_locale,
                allowed_av_ids=allowed_av_ids,
                allowed_attr_codes=allowed_attr_codes,
            )
            mapped += mapped_ai
            self.stdout.write(
                self.style.SUCCESS(f"Mapped keywords for run {run_id} (mode=ai): {mapped} mappings{' (dry-run)' if dry else ''}")
            )
            return

    def _map_rules(self, prk_qs, run, lexicon, *, dry: bool, intent_gate: bool, intent_threshold: float) -> int:
        mapped = 0
        ctx = transaction.atomic() if not dry else nullcontext()
        with ctx:
            for prk in prk_qs:
                kw = prk.keyword
                phrases = []
                parse = KeywordParse.objects.filter(keyword=kw).order_by("-updated_at").first()
                if intent_gate and not self._intent_allows(keyword=kw, parse=parse, dry=dry, threshold=intent_threshold):
                    continue
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
                                match = pair
                                match_type = "contains"
                                matched_term = key_term
                                break
                    if not match:
                        continue
                    attr, aval = match
                    conf = 1.0 if match_type == "exact" else 0.6
                    if dry:
                        mapped += 1
                        continue
                    AttributeMap.objects.update_or_create(
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
                    mapped += 1
        return mapped

    def _call_llm(self, payload: dict) -> Optional[List[dict]]:
        """
        Call an LLM to pick attribute_value_id from the provided shortlist.
        Expects payload containing:
          - keyword (str)
          - phrases (list[str])
          - detected (dict)
          - shortlist: {attr_id: {"code": str, "values": [{"id": int, "label": str}]}}
          - product_context_terms (list[str])
          - product_type_label/main_category for context
        Returns a list of {"attribute_value_id": int, "confidence": float}.
        """
        try:
            from openai import OpenAI
        except Exception as exc:
            print("LLM client not available:", exc)
            return None

        # Flatten shortlist for prompt readability, but guard allowed ids.
        allowed_ids = {
            v["id"] for attr in (payload.get("shortlist") or {}).values() for v in attr.get("values", [])
        }
        if not allowed_ids:
            return []

        api_key = os.getenv("OPENAI_API_KEY") or getattr(settings, "OPENAI_API_KEY", None)
        if not api_key:
            print("LLM: OPENAI_API_KEY not set.")
            return None

        client = OpenAI(api_key=api_key)

        system_prompt = (
            "You are a precise mapper for product attributes and values.\n"
            "Choose attribute_value_id only from the provided shortlist.\n"
            "Product type context is provided; use it to avoid mismatching values from other categories.\n"
            "Product context terms may help disambiguate, but evidence must still come from the keyword/phrases.\n"
            "Respond with JSON: {\"mappings\": ["
            "{\"attribute_code\": \"<code>\", \"attribute_value_id\": <int>, \"confidence\": <0-1>, \"evidence\": \"token from keyword\"}"
            "]}\n"
            "Rules:\n"
            "- Evidence must be a literal substring of the keyword or the provided phrases.\n"
            "- At most one mapping per attribute_code.\n"
            "- If unsure, return an empty mappings list. Do not guess or invent ids."
        )
        user_content = {
            "keyword": payload.get("keyword"),
            "phrases": payload.get("phrases"),
            "detected": payload.get("detected"),
            "shortlist": payload.get("shortlist"),
            "product_context_terms": payload.get("product_context_terms"),
            "product_type": payload.get("product_type"),
            "product_type_label": payload.get("product_type_label"),
            "product_type_main_category": payload.get("product_type_main_category"),
        }

        model_name = os.getenv("OPENAI_MODEL", getattr(settings, "OPENAI_MODEL", "gpt-4o-mini"))

        def do_call(use_response_format: bool = True):
            return client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(user_content, ensure_ascii=False)},
                ],
                temperature=0,
                max_tokens=300,
                **({"response_format": {"type": "json_object"}} if use_response_format else {}),
            )

        try:
            resp = do_call(use_response_format=True)
            text = resp.choices[0].message.content
        except Exception as exc:
            # Retry without response_format if the API rejects the json_object constraint
            print("LLM call failed with response_format, retrying without it:", exc)
            try:
                resp = do_call(use_response_format=False)
                text = resp.choices[0].message.content
            except Exception as exc2:
                print("LLM call failed:", exc2)
                return None

        try:
            data = json.loads(text or "{}")
        except Exception as exc:
            print("LLM JSON parse failed:", exc, "raw:", text)
            return None

        results = []
        for m in data.get("mappings", []) or []:
            aval_id = m.get("attribute_value_id")
            # Optional attribute_code from the model for audit/debug
            attr_code = m.get("attribute_code")
            if aval_id not in allowed_ids:
                continue
            conf = m.get("confidence")
            try:
                conf = float(conf) if conf is not None else None
            except Exception:
                conf = None
            results.append(
                {
                    "attribute_code": attr_code,
                    "attribute_value_id": aval_id,
                    "confidence": conf,
                    "evidence": (m.get("evidence") or "").strip(),
                    "model": model_name,
                }
            )
        return results

    def _intent_allows(self, *, keyword, parse: Optional[KeywordParse], dry: bool, threshold: float) -> bool:
        cached = None
        if parse and isinstance(parse.detected, dict):
            cached = parse.detected.get("intent_gate")
        if cached and isinstance(cached, dict):
            intent = cached.get("intent")
            conf = cached.get("confidence")
            try:
                conf_val = float(conf) if conf is not None else None
            except Exception:
                conf_val = None
            if intent and intent != "product" and conf_val is not None and conf_val >= threshold:
                return False
            return True

        result = self._llm_intent_gate(keyword.term or "")
        if result and parse and not dry:
            detected = parse.detected or {}
            detected["intent_gate"] = result
            parse.detected = detected
            parse.save(update_fields=["detected", "updated_at"])

        intent = result.get("intent") if isinstance(result, dict) else None
        conf = result.get("confidence") if isinstance(result, dict) else None
        try:
            conf_val = float(conf) if conf is not None else None
        except Exception:
            conf_val = None
        if intent and intent != "product" and conf_val is not None and conf_val >= threshold:
            return False
        return True

    def _llm_intent_gate(self, keyword: str) -> dict:
        try:
            from openai import OpenAI
        except Exception as exc:
            print("LLM client not available:", exc)
            return {"intent": "product", "confidence": 0.0, "evidence": ""}

        api_key = os.getenv("OPENAI_API_KEY") or getattr(settings, "OPENAI_API_KEY", None)
        if not api_key:
            print("LLM: OPENAI_API_KEY not set.")
            return {"intent": "product", "confidence": 0.0, "evidence": ""}

        client = OpenAI(api_key=api_key)
        model_name = os.getenv("OPENAI_MODEL", getattr(settings, "OPENAI_MODEL", "gpt-4o-mini"))

        system_prompt = (
            "Classify search keyword intent. Output strict JSON: "
            "{\"intent\":\"product|price|support|marketplace|other\",\"confidence\":0-1,\"evidence\":\"literal substring\"}. "
            "Evidence must be a literal substring of the keyword."
        )

        def do_call(use_response_format: bool = True):
            return client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": keyword},
                ],
                temperature=0,
                max_tokens=120,
                **({"response_format": {"type": "json_object"}} if use_response_format else {}),
            )

        try:
            resp = do_call(use_response_format=True)
            text = resp.choices[0].message.content
        except Exception as exc:
            print("LLM call failed with response_format, retrying without it:", exc)
            try:
                resp = do_call(use_response_format=False)
                text = resp.choices[0].message.content
            except Exception as exc2:
                print("LLM call failed:", exc2)
                return {"intent": "product", "confidence": 0.0, "evidence": ""}

        try:
            data = json.loads(text or "{}")
        except Exception as exc:
            print("LLM JSON parse failed:", exc, "raw:", text)
            return {"intent": "product", "confidence": 0.0, "evidence": ""}
        data["model"] = model_name
        return data

    def _map_ai(
        self,
        *,
        run: PlannerRun,
        limit: Optional[int],
        dry: bool,
        intent_gate: bool,
        intent_threshold: float,
        fallback_rules: bool,
        context_max_products: int,
        context_max_terms: int,
        context_max_ngram: int,
        context_min_df: int,
        context_max_df_ratio: float,
        context_debug: bool,
        context_ignore_source_locale: bool,
        allowed_av_ids: Optional[set[int]],
        allowed_attr_codes: Optional[set[str]],
    ) -> int:
        # Unmapped keywords only, ordered by volume (max avg_searches across metrics)
        mapped_ids = set(
            AttributeMap.objects.filter(Q(origin_run_keyword__run=run) | Q(keyword__planner_runs__run=run))
            .values_list("keyword_id", flat=True)
            .distinct()
        )
        prk_qs = (
            PlannerRunKeyword.objects.filter(run=run)
            .exclude(keyword_id__in=mapped_ids)
            .annotate(vol=Max("keyword__metrics__avg_searches"))
            .order_by("-vol")
            .select_related("keyword")
        )
        if limit:
            prk_qs = prk_qs[:limit]
        if not prk_qs.exists():
            self.stdout.write(self.style.WARNING("No unmapped keywords found for AI."))
            return 0

        if allowed_av_ids is not None and not allowed_av_ids:
            self.stdout.write(self.style.WARNING("No attribute values found for this product type; nothing to map."))
            return 0

        # Precompute candidate values per attribute (filtered to allowed attributes when configured)
        candidate_values: Dict[int, Dict[str, object]] = {}
        val_terms: Dict[int, List[str]] = {}

        av_qs = AttributeValue.objects.select_related("attribute")
        if allowed_av_ids is not None:
            av_qs = av_qs.filter(id__in=allowed_av_ids)
        if allowed_attr_codes:
            av_qs = av_qs.filter(attribute__code__in=allowed_attr_codes)
        for av in av_qs:
            terms = _candidate_terms_for_value(av, locale=run.locale, channel=run.channel)
            val_terms[av.id] = terms
            candidate_values.setdefault(
                av.attribute_id,
                {"code": av.attribute.code, "values": []},
            )
            candidate_values[av.attribute_id]["values"].append({"id": av.id, "terms": terms, "label": terms[0] if terms else av.code})

        mapped = 0
        fallback_lexicon = None
        product_context_terms, context_stats = _product_description_terms(
            run=run,
            max_products=context_max_products,
            max_terms=context_max_terms,
            max_ngram=context_max_ngram,
            min_df=context_min_df,
            max_df_ratio=context_max_df_ratio,
            ignore_source_locale=context_ignore_source_locale,
        )
        if context_debug:
            sample = ", ".join(product_context_terms[:12])
            self.stdout.write(
                self.style.NOTICE(
                    "Context terms: "
                    f"source={context_stats.get('source')} "
                    f"i18n_rows={context_stats.get('i18n_rows_sampled')} "
                    f"source_rows={context_stats.get('source_rows_sampled')} "
                    f"docs_used={context_stats.get('docs_used')} "
                    f"terms_total={context_stats.get('terms_total')} "
                    f"terms_returned={context_stats.get('terms_returned')} "
                    f"sample=[{sample}]"
                )
            )
        ctx = transaction.atomic() if not dry else nullcontext()
        with ctx:
            for prk in prk_qs:
                kw = prk.keyword
                parse = KeywordParse.objects.filter(keyword=kw).order_by("-updated_at").first()
                phrases = parse.phrases if parse and parse.phrases else _phrases_from_term(kw.term or "")
                detected = parse.detected if parse else {}
                if intent_gate and not self._intent_allows(
                    keyword=kw, parse=parse, dry=dry, threshold=intent_threshold
                ):
                    continue

                # Build shortlist per attribute by overlap score
                shortlist: Dict[int, Dict[str, object]] = {}
                for attr_id, data in candidate_values.items():
                    scored = []
                    for entry in data["values"]:
                        score = _score_overlap(phrases, entry["terms"])
                        scored.append((score, entry))
                    scored.sort(key=lambda x: x[0], reverse=True)
                    top = [entry for sc, entry in scored if sc > 0][:15]
                    if top:
                        shortlist[attr_id] = {
                            "code": data["code"],
                            "values": [{"id": e["id"], "label": e["label"]} for e in top],
                        }
                if not shortlist:
                    continue

                payload = {
                    "keyword": kw.term,
                    "phrases": phrases,
                    "detected": detected,
                    "shortlist": shortlist,
                    "product_context_terms": product_context_terms,
                    "locale": run.locale.code,
                    "product_type": run.product_type.code if run.product_type else None,
                    "product_type_label": run.product_type.default_label if run.product_type else None,
                    "product_type_main_category": run.product_type.main_category if run.product_type else None,
                    "channel": run.channel.code if run.channel else None,
                }
                results = self._call_llm(payload)
                if results is None:
                    if fallback_rules:
                        if fallback_lexicon is None:
                            fallback_lexicon = _lexicon_for_values(
                                locale=run.locale,
                                channel=run.channel,
                                allowed_av_ids=allowed_av_ids,
                            )
                        mapped += self._map_rules(
                            [prk],
                            run,
                            fallback_lexicon,
                            dry=dry,
                            intent_gate=intent_gate,
                            intent_threshold=intent_threshold,
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"LLM unavailable for keyword id={kw.id} term='{kw.term}'; skipping."
                            )
                        )
                    continue
                if fallback_rules and not results:
                    if fallback_lexicon is None:
                        fallback_lexicon = _lexicon_for_values(
                            locale=run.locale,
                            channel=run.channel,
                            allowed_av_ids=allowed_av_ids,
                        )
                    mapped += self._map_rules(
                        [prk],
                        run,
                        fallback_lexicon,
                        dry=dry,
                        intent_gate=intent_gate,
                        intent_threshold=intent_threshold,
                    )
                    continue
                kw_text_lower = (kw.term or "").lower()
                phrase_set = {p.lower() for p in phrases}
                for res in results or []:
                    aval_id = res.get("attribute_value_id")
                    confidence = res.get("confidence") or None
                    evidence = (res.get("evidence") or "").strip().lower()
                    if not evidence:
                        continue
                    if not aval_id:
                        continue
                    try:
                        aval = AttributeValue.objects.get(id=aval_id)
                    except AttributeValue.DoesNotExist:
                        continue
                    candidate_terms = val_terms.get(aval_id, [])
                    # Evidence must be present and found in keyword/phrases
                    if evidence and (evidence not in kw_text_lower) and all(evidence not in p for p in phrase_set):
                        continue
                    # Evidence should align with candidate terms
                    if evidence and candidate_terms:
                        if not any(
                            evidence == t.lower() or evidence in t.lower() or t.lower() in evidence for t in candidate_terms
                        ):
                            continue
                    # Enforce a higher confidence bar for AI-suggested mappings
                    try:
                        conf_val = float(confidence) if confidence is not None else None
                    except Exception:
                        conf_val = None
                    if conf_val is not None and conf_val < 0.8:
                        continue
                    attr = aval.attribute
                    if dry:
                        mapped += 1
                        continue
                    AttributeMap.objects.update_or_create(
                        keyword=kw,
                        attribute=attr,
                        attribute_value=aval,
                        defaults={
                            "confidence": confidence,
                            "status": AttributeMap.Status.SUGGESTED,
                            "tagged_by": "llm",
                            "origin_run_keyword": prk,
                            "reason": "llm_shortlist",
                            "reason_code": "llm",
                            "evidence": {
                                "evidence": evidence,
                                "model": res.get("model"),
                                "prompt_version": "ai_map_v1",
                                "attribute_code": attr.code,
                                "phrases": phrases,
                                "candidate_terms": candidate_terms,
                            },
                        },
                    )
                    mapped += 1
        return mapped
