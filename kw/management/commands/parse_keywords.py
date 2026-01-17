from __future__ import annotations

import re
from collections import Counter
from typing import Iterable, List, Optional, Set

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from content.models import AttributeValueI18n, AttributeValueSynonym, Channel, Locale
from kw.models import KeywordParse, PlannerRun, PlannerRunKeyword


TOKEN_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*", re.IGNORECASE)
SIZE_RE = re.compile(r"\b(\d{2,4})\s*[x×]\s*(\d{2,4})(?:\s*(cm|mm))?\b", re.IGNORECASE)
CURRENCY_RE = re.compile(r"[€$£]|\b(?:eur|usd|gbp)\b", re.IGNORECASE)
FILE_EXT_RE = re.compile(r"\.(pdf|docx?|xlsx?|zip|rar)\b", re.IGNORECASE)
URL_RE = re.compile(r"https?://|www\.", re.IGNORECASE)


def _normalize_term(term: str) -> str:
    term = (term or "").strip().lower()
    term = term.replace("×", "x")
    term = re.sub(r"\s+", " ", term)
    return term


def _tokenize(term: str) -> List[str]:
    return [m.group(0).lower() for m in TOKEN_RE.finditer(term)]


def _ngram_tokens(tokens: List[str], n: int) -> Iterable[str]:
    for i in range(len(tokens) - n + 1):
        yield " ".join(tokens[i : i + n])


def _build_scope_lexicon_terms(*, locale: Locale, channel: Optional[Channel]) -> Set[str]:
    """
    Tokens that appear in approved synonyms or i18n labels should not be auto-stopworded.
    """
    terms: List[str] = []
    syn_qs = (
        AttributeValueSynonym.objects.filter(
            locale=locale,
            status=AttributeValueSynonym.Status.APPROVED,
        )
        .filter(Q(channel=channel) | Q(channel__isnull=True))
        .values_list("term", flat=True)
    )
    terms.extend(list(syn_qs))

    lbl_qs = AttributeValueI18n.objects.filter(locale=locale).values_list("label", flat=True)
    terms.extend(list(lbl_qs))

    lex_tokens: Set[str] = set()
    for t in terms:
        norm = _normalize_term(t)
        norm = SIZE_RE.sub(" ", norm)
        for tok in _tokenize(norm):
            if tok and not tok.isdigit():
                lex_tokens.add(tok)
    return lex_tokens


def _learn_stopwords_for_run(
    *,
    prk_qs,
    lex_tokens: Set[str],
    df_ratio_threshold: float = 0.35,
    min_token_len: int = 2,
) -> Set[str]:
    df = Counter()
    total = 0
    for prk in prk_qs:
        total += 1
        term = _normalize_term(prk.keyword.term or "")
        term = SIZE_RE.sub(" ", term)
        toks = set(_tokenize(term))
        for tok in toks:
            df[tok] += 1

    if total == 0:
        return set()

    stop: Set[str] = set()
    for tok, c in df.items():
        if tok.isdigit():
            continue
        if len(tok) < min_token_len:
            continue
        if tok in lex_tokens:
            continue
        if (c / total) >= df_ratio_threshold:
            stop.add(tok)
    return stop


def _parse(term: str, *, stopwords: Optional[Set[str]] = None) -> dict:
    norm = _normalize_term(term)
    detected_sizes = [f"{w}x{h}{(' ' + unit) if unit else ''}" for w, h, unit in SIZE_RE.findall(norm)]
    norm_wo_sizes = SIZE_RE.sub(" ", norm)

    has_currency = bool(CURRENCY_RE.search(norm_wo_sizes))
    has_url = bool(URL_RE.search(norm_wo_sizes))
    has_file = bool(FILE_EXT_RE.search(norm_wo_sizes))

    tokens = _tokenize(norm_wo_sizes)

    tokens_clean: List[str] = []
    for tok in tokens:
        if stopwords and tok in stopwords:
            continue
        if tok.isdigit():
            continue
        tokens_clean.append(tok)

    phrases: List[str] = []
    for n in (1, 2, 3):
        phrases.extend(list(_ngram_tokens(tokens_clean, n)))

    detected = {
        "sizes": detected_sizes,
        "has_currency": has_currency,
        "has_url": has_url,
        "has_file": has_file,
        "price_intent": bool(has_currency),
        "intent_flags": [],
    }
    return {
        "tokens": tokens_clean,
        "phrases": phrases,
        "detected": detected,
        "normalized": norm,
    }


class Command(BaseCommand):
    help = (
        "Parse keywords into KeywordParse (tokens, phrases, detected signals).\n"
        "Usage: parse_keywords --run <planner_run_id> [--limit N] [--dry-run]"
    )

    def add_arguments(self, parser):
        parser.add_argument("--run", type=int, required=True, help="PlannerRun id to parse keywords from.")
        parser.add_argument("--limit", type=int, default=None, help="Optional limit of keywords to parse.")
        parser.add_argument("--dry-run", action="store_true", help="Do not write to DB.")
        parser.add_argument("--debug", action="store_true", help="Print parsed output per keyword.")
        parser.add_argument(
            "--no-learn-stopwords",
            action="store_true",
            help="Disable auto stopword learning for this run.",
        )
        parser.add_argument(
            "--df-ratio",
            type=float,
            default=0.35,
            help="Doc-frequency ratio threshold for auto stopwords (default 0.35).",
        )

    def handle(self, *args, **opts):
        run_id = opts["run"]
        limit = opts["limit"]
        dry = opts["dry_run"]
        debug = opts["debug"]
        learn_stopwords = not opts["no_learn_stopwords"]
        df_ratio = opts["df_ratio"]

        run = PlannerRun.objects.select_related("locale", "channel").filter(id=run_id).first()
        if not run:
            raise CommandError(f"PlannerRun {run_id} not found")

        prk_qs = PlannerRunKeyword.objects.filter(run_id=run_id).select_related("keyword")
        if limit:
            prk_qs = prk_qs[:limit]
        if not prk_qs.exists():
            raise CommandError(f"No PlannerRunKeyword found for run {run_id}")

        stopwords: Set[str] = set()
        if learn_stopwords:
            lex_tokens = _build_scope_lexicon_terms(locale=run.locale, channel=run.channel)
            stopwords = _learn_stopwords_for_run(
                prk_qs=prk_qs,
                lex_tokens=lex_tokens,
                df_ratio_threshold=df_ratio,
            )

        parsed = 0
        with transaction.atomic():
            for prk in prk_qs:
                kw = prk.keyword
                term = kw.term or ""
                parsed_data = _parse(term, stopwords=stopwords)
                if debug:
                    self.stdout.write(
                        f"[kw={kw.id}] term={term!r} "
                        f"normalized={parsed_data['normalized']!r} "
                        f"tokens={parsed_data['tokens']} "
                        f"phrases={parsed_data['phrases']} "
                        f"detected={parsed_data['detected']}"
                    )
                if dry:
                    continue
                KeywordParse.objects.update_or_create(
                    keyword=kw,
                    defaults={
                        "tokens": parsed_data["tokens"],
                        "phrases": parsed_data["phrases"],
                        "detected": parsed_data["detected"],
                        "source": "rules",
                        "tagged_by": "parse_keywords_cmd",
                    },
                )
                parsed += 1
