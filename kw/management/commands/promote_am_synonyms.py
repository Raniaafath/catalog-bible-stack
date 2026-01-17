from __future__ import annotations

import json
import os
import re
from typing import List, Optional, Set, Tuple

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from content.models import AttributeValueSynonym, Channel, Locale
from kw.models import AttributeMap, PlannerRun


SIZE_RE = re.compile(r"\b(\d{2,4})\s*[x×]\s*(\d{2,4})(?:\s*(cm|mm))?\b", re.IGNORECASE)
CURRENCY_RE = re.compile(r"[€$£]|\b(?:eur|usd|gbp)\b", re.IGNORECASE)
FILE_EXT_RE = re.compile(r"\.(pdf|docx?|xlsx?|zip|rar)\b", re.IGNORECASE)
URL_RE = re.compile(r"https?://|www\.", re.IGNORECASE)


def _normalize_term(term: str) -> str:
    term = (term or "").strip()
    return re.sub(r"\s+", " ", term)


def _tokenize(text: str) -> List[str]:
    text = _normalize_term(text.lower())
    return re.findall(r"[^\W\d_]+(?:'[^\W\d_]+)?|\d+(?:x\d+)?", text, flags=re.UNICODE)


def _strip_tokens(tokens: List[str], head_terms: Set[str], stopwords: Set[str]) -> List[str]:
    cleaned = []
    for tok in tokens:
        if not tok:
            continue
        if tok in stopwords:
            continue
        if tok in head_terms:
            continue
        if re.match(r"^\d+(?:x\d+)?$", tok):  # sizes like 140x80 or 80
            continue
        cleaned.append(tok)
    return cleaned


def _jaccard(a: Set[str], b: Set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _get_target_terms(am: AttributeMap, locale: Locale, channel: Channel, head_terms: Set[str], stopwords: Set[str]) -> List[str]:
    """
    Collect attribute value label + existing synonyms for overlap scoring.
    Adjust field names if your i18n model differs.
    """
    av = am.attribute_value
    if not av:
        return []

    terms: List[str] = []

    # Localized label (AttributeValueI18n)
    if hasattr(av, "i18n"):
        row = av.i18n.filter(locale=locale).first()
        if row:
            lbl = getattr(row, "label", None) or getattr(row, "term", None) or getattr(row, "name", None)
            if lbl:
                terms.append(str(lbl))

    # Existing synonyms (channel-specific or global)
    syn_qs = AttributeValueSynonym.objects.filter(attribute_value=av, locale=locale).filter(
        Q(channel=channel) | Q(channel__isnull=True)
    )
    terms.extend(list(syn_qs.values_list("term", flat=True)))

    # Fallback to code
    if getattr(av, "code", None):
        terms.append(av.code)

    # Dedupe
    out: List[str] = []
    seen: Set[str] = set()
    for t in terms:
        t_clean = (t or "").strip()
        if not t_clean:
            continue
        # Drop target terms that already contain head terms to avoid polluting matches.
        ttoks = _strip_tokens(_tokenize(t_clean), set(), stopwords)
        if not ttoks or any(tok in head_terms for tok in ttoks):
            continue
        k = t_clean.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(t_clean)
    return out


def _best_span_from_keyword(
    keyword_term: str,
    target_terms: List[str],
    head_terms: Set[str],
    stopwords: Set[str],
    max_window: int = 4,
    threshold: float = 0.34,
) -> Optional[str]:
    ktoks = _strip_tokens(_tokenize(keyword_term), head_terms, stopwords)
    if not ktoks:
        return None

    target_sets: List[Set[str]] = []
    for t in target_terms:
        ttoks = _strip_tokens(_tokenize(t), set(), stopwords)  # do not strip heads from value label
        if ttoks:
            target_sets.append(set(ttoks))
    if not target_sets:
        return None

    best_score = 0.0
    best_phrase: Optional[str] = None

    for w in range(1, max_window + 1):
        for i in range(0, len(ktoks) - w + 1):
            span = ktoks[i : i + w]
            span_set = set(span)
            score = 0.0
            for ts in target_sets:
                # Overlap score
                score = max(score, _jaccard(span_set, ts))
                # Substring bonus: if any target token is contained in any span token (e.g., marmoresina contains resina)
                if any(any(tt in st or st in tt for st in span_set) for tt in ts):
                    score = max(score, 0.9)
            if score > best_score:
                best_score = score
                best_phrase = " ".join(span)

    return _normalize_term(best_phrase) if best_phrase and best_score >= threshold else None


def _extract_token(
    am: AttributeMap,
    head_terms: Set[str],
    stopwords: Set[str],
    locale: Locale,
    channel: Channel,
) -> Optional[str]:
    # Target-aware span first
    if am.keyword and am.keyword.term and am.attribute_value_id:
        target_terms = _get_target_terms(am, locale, channel, head_terms, stopwords)
        span = _best_span_from_keyword(am.keyword.term, target_terms, head_terms, stopwords)
        if span:
            return span

    # Evidence fallback
    evidence = am.evidence or {}
    for key in ("matched_phrase", "lexicon_term", "evidence"):
        val = evidence.get(key)
        if isinstance(val, str) and val.strip():
            toks = _strip_tokens(_tokenize(val), head_terms, stopwords)
            if toks:
                return _normalize_term(" ".join(toks[:2]))

    # Keyword fallback (last resort)
    if am.keyword and am.keyword.term:
        toks = _strip_tokens(_tokenize(am.keyword.term), head_terms, stopwords)
        if toks:
            return _normalize_term(" ".join(toks[:2]))

    return None


def _is_invalid_token(token: str, head_terms: Set[str], stopwords: Set[str]) -> bool:
    if not token or len(token) > 60:
        return True
    if SIZE_RE.search(token) or CURRENCY_RE.search(token):
        return True
    if URL_RE.search(token) or FILE_EXT_RE.search(token):
        return True
    tokens = _tokenize(token)
    if not tokens:
        return True
    for tok in tokens:
        if tok in head_terms or tok in stopwords:
            return True
        if tok.isdigit():
            return True
    return False


def _ai_client() -> Optional[Tuple[object, str]]:
    try:
        from openai import OpenAI
    except Exception as exc:
        print("LLM client not available:", exc)
        return None

    api_key = os.getenv("OPENAI_API_KEY") or getattr(settings, "OPENAI_API_KEY", None)
    if not api_key:
        print("LLM: OPENAI_API_KEY not set.")
        return None
    model_name = os.getenv("OPENAI_MODEL", getattr(settings, "OPENAI_MODEL", "gpt-4o-mini"))
    return (OpenAI(api_key=api_key), model_name)


def _extract_token_ai(
    am: AttributeMap,
    head_terms: Set[str],
    stopwords: Set[str],
    locale: Locale,
    channel: Channel,
    *,
    client,
    model_name: str,
) -> Optional[str]:
    keyword_term = (am.keyword.term or "").strip()
    if not keyword_term:
        return None
    target_terms = _get_target_terms(am, locale, channel, head_terms, stopwords)
    if not target_terms:
        return None

    system_prompt = (
        "You pick a short synonym token for a product attribute value.\n"
        "Return JSON: {\"token\": \"<string or null>\"}.\n"
        "Rules:\n"
        "- Token must be 1-2 words, max 30 chars, letters/numbers/hyphens only.\n"
        "- Token should be a substring of the keyword OR one of the target terms.\n"
        "- Do not include head terms, sizes, prices, or intent words.\n"
        "- If unsure, return null."
    )
    payload = {
        "keyword": keyword_term,
        "target_terms": target_terms[:10],
        "head_terms": sorted(head_terms)[:20],
        "stopwords": sorted(stopwords)[:20],
    }

    def do_call(use_response_format: bool = True):
        return client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            temperature=0,
            max_tokens=80,
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
            return None

    try:
        data = json.loads(text or "{}")
    except Exception as exc:
        print("LLM JSON parse failed:", exc, "raw:", text)
        return None

    token = (data.get("token") or "").strip()
    if not token:
        return None
    token_norm = _normalize_term(token)
    if _is_invalid_token(token_norm, head_terms, stopwords):
        return None
    return token_norm


class Command(BaseCommand):
    help = (
        "Create approved AttributeValueSynonym rows from approved AttributeMap evidence tokens "
        "so keyword-derived phrasing can be rendered. "
        "Usage: promote_am_synonyms --locale <code> --channel <code> [--run <id>] [--limit N] [--dry-run]"
    )

    def add_arguments(self, parser):
        parser.add_argument("--locale", required=True, help="Locale code.")
        parser.add_argument("--channel", required=True, help="Channel code.")
        parser.add_argument("--run", type=int, default=None, help="Optional PlannerRun id to scope origin_run_keyword.")
        parser.add_argument("--limit", type=int, default=None, help="Optional max AttributeMap rows to process.")
        parser.add_argument("--dry-run", action="store_true", help="Do not write to DB.")
        parser.add_argument("--mode", choices=["rules", "ai"], default="rules", help="Token selection mode.")
        parser.add_argument(
            "--head-terms",
            default="",
            help="Comma-separated custom head terms to strip (in addition to product type labels/synonyms).",
        )
        parser.add_argument(
            "--stopwords",
            default="",
            help="Comma-separated stopwords to strip (intent/functional words) in addition to size removal.",
        )

    def handle(self, *args, **opts):
        locale_code = opts["locale"]
        channel_code = opts["channel"]
        run_id = opts["run"]
        limit = opts["limit"]
        dry = opts["dry_run"]
        mode = opts["mode"]

        locale = Locale.objects.filter(code=locale_code).first()
        if not locale:
            raise CommandError(f"Locale {locale_code} not found")
        channel = Channel.objects.filter(code=channel_code).first()
        if not channel:
            raise CommandError(f"Channel {channel_code} not found")

        qs = (
            AttributeMap.objects.filter(
                status=AttributeMap.Status.APPROVED,
                attribute_value__isnull=False,
                keyword__locale=locale,
            )
            .select_related("attribute_value", "keyword")
            .filter(
                Q(origin_run_keyword__run__channel=channel)
                | Q(keyword__planner_runs__run__channel=channel)
            )
            .order_by("-confidence", "id")
        )
        if run_id:
            run = PlannerRun.objects.filter(id=run_id).first()
            if not run:
                raise CommandError(f"PlannerRun {run_id} not found")
            qs = qs.filter(
                Q(origin_run_keyword__run=run)
                | Q(keyword__planner_runs__run=run)
            )
        if limit:
            qs = qs[:limit]
        if not qs.exists():
            self.stdout.write(self.style.WARNING("No approved AttributeMap rows found for given scope."))
            return

        stopwords: Set[str] = set()
        if opts.get("stopwords"):
            stopwords.update([t.strip().lower() for t in opts["stopwords"].split(",") if t.strip()])

        # Head terms from product type labels/synonyms + overrides
        head_terms: Set[str] = set()
        run_ids = list(
            qs.exclude(origin_run_keyword__run__isnull=True)
            .values_list("origin_run_keyword__run_id", flat=True)
            .distinct()
        )
        run_ids += list(
            qs.filter(origin_run_keyword__run__isnull=True)
            .values_list("keyword__planner_runs__run_id", flat=True)
            .distinct()
        )
        run_ids = [rid for rid in run_ids if rid]
        if run_ids:
            for pr in PlannerRun.objects.filter(id__in=run_ids).select_related("product_type"):
                if pr.product_type:
                    label = pr.product_type.default_label or ""
                    head_terms.update(_strip_tokens(_tokenize(label), set(), stopwords))
                    for syn in pr.product_type.synonyms.filter(locale=locale):
                        head_terms.update(_strip_tokens(_tokenize(syn.term), set(), stopwords))
        if opts.get("head_terms"):
            custom_heads = [t.strip().lower() for t in opts["head_terms"].split(",") if t.strip()]
            head_terms.update(custom_heads)

        created = 0
        skipped_exists = 0
        skipped_empty = 0
        llm_client = None
        llm_model = None
        ai_fallback = False

        if mode == "ai":
            client_info = _ai_client()
            if client_info:
                llm_client, llm_model = client_info
            else:
                ai_fallback = True

        with transaction.atomic():
            for amap in qs:
                if mode == "ai" and llm_client:
                    token = _extract_token_ai(
                        amap,
                        head_terms,
                        stopwords,
                        locale,
                        channel,
                        client=llm_client,
                        model_name=llm_model,
                    )
                else:
                    token = _extract_token(amap, head_terms, stopwords, locale, channel)
                    if ai_fallback and mode == "ai":
                        ai_fallback = False
                        self.stdout.write(self.style.WARNING("AI unavailable; falling back to rules."))

                if not token or _is_invalid_token(token, head_terms, stopwords):
                    skipped_empty += 1
                    continue

                exists = AttributeValueSynonym.objects.filter(
                    attribute_value=amap.attribute_value,
                    locale=locale,
                    channel=channel,
                    term__iexact=token,
                ).exists()
                if exists:
                    skipped_exists += 1
                    continue

                if dry:
                    created += 1
                    continue

                reason = (
                    "promoted from AttributeMap evidence (ai token)"
                    if mode == "ai" and llm_client
                    else "promoted from AttributeMap evidence (target-aware span)"
                )
                source = "am_ai" if mode == "ai" and llm_client else "am_evidence"
                AttributeValueSynonym.objects.create(
                    attribute_value=amap.attribute_value,
                    locale=locale,
                    channel=channel,
                    term=token,
                    status=AttributeValueSynonym.Status.APPROVED,
                    source=source,
                    reason=reason,
                    keyword=amap.keyword,
                    score=amap.confidence,
                )
                created += 1

            if dry:
                transaction.set_rollback(True)

        self.stdout.write(
            self.style.SUCCESS(
                f"{'[DRY-RUN] ' if dry else ''}Synonyms created: {created} | "
                f"skipped existing: {skipped_exists} | skipped empty/invalid: {skipped_empty}"
            )
        )
