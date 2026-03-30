from __future__ import annotations

import re
from collections import Counter
from typing import Iterable, List, Tuple

from django.conf import settings
from django.db.models import Q

from catalog.models import Product, ProductAttributeValue, ProductType
from content.models import (
    AttributeValueI18n,
    AttributeValueSynonym,
    Locale,
    ProductTypeI18n,
    ProductTypeSynonym,
    SynonymStatus,
)
from kw.models import PlannerSeed

SeedTerm = str | tuple[str, str]

# Minimal intent/negative tokens to avoid seeding
INTENT_STOPWORDS = {
    "preis",
    "price",
    "billig",
    "cheap",
    "kostenlos",
    "free",
    "gebraucht",
    "used",
    "review",
    "test",
    "install",
    "montage",
    "repair",
    "reparatur",
    "pdf",
    "manual",
    "job",
}

# Junk tokens/stopwords/units that should never become seeds
JUNK_STOPWORDS = {
    "li",
    "ul",
    "cm",
    "mm",
    "und",
    "et",
    "or",
    "and",
    "de",
    "la",
    "le",
    "des",
    "du",
    "en",
    "avec",
    "pour",
    "sans",
}

TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")
PLACEHOLDER_TERMS = {
    "nicht betroffen",
    "non concern",
    "non concerné",
    "non pertinente",
    "non pertinenza",
    "n/a",
    "na",
    "optional",
    "aucun",
    "aucune",
    "sans objet",
    "not applicable",
}
DIMENSION_RE = re.compile(r"^\d{2,4}\s*(?:[x×]\s*\d{2,4})+(?:\s*(?:cm|mm))?$", re.I)

# Title-eligible attribute codes per product_type code (quick config without migration).
# Empty by default — filtering is driven by Attribute.use_in_title in the database.
TITLE_ELIGIBLE_ATTRS_BY_PT: dict[str, set[str]] = {}


def _looks_like_sku_or_slug(term: str) -> bool:
    # e.g., "duschwanne-moderne-140x80", "rc14080hdsl-9010-line-ob"
    if "-" in term and re.search(r"\d", term):
        return True
    if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+){2,}", term) and re.search(r"\d", term):
        return True
    return False


def _looks_like_brand(term: str) -> bool:
    return ("'" in term) or ("’" in term) or (term.isupper() and len(term) >= 5)


def build_seeds(
    *,
    locale: Locale,
    product_type: ProductType,
    channel,
    max_seeds: int = 8,
) -> List[str]:
    """
    Deterministically build seed terms for a (product_type, locale, channel).
    Always returns at least the localized product type label.
    """
    items = build_seed_items(locale=locale, product_type=product_type, channel=channel, max_seeds=max_seeds)
    # Return plain terms for downstream consumers (e.g., Google Ads request)
    return [term for term, _seed_type in items]


def build_seeds_debug(
    *,
    locale: Locale,
    product_type: ProductType,
    channel,
    max_seeds: int = 8,
) -> dict:
    """
    Debug helper: return seeds plus the contributing components.
    """
    pt_label = _product_type_label(locale, product_type)
    pt_label_clean = _sanitize_term(pt_label)
    label_frags = [pt_label_clean] if pt_label_clean else []
    label_frags.extend([frag for frag in _label_fragments(pt_label, max_fragments=4) if frag != pt_label_clean])

    synonyms = [_sanitize_term(term) for term in _product_type_synonyms(locale, product_type, channel)]
    synonyms = [s for s in synonyms if s]

    value_terms_raw = _attribute_value_terms(locale, product_type, channel, limit=40)
    value_terms = [_sanitize_term(v) for v in value_terms_raw if _sanitize_term(v)]

    corpus_raw = _top_corpus_terms(locale, product_type, limit=10)
    corpus_terms = []
    for term, score in corpus_raw:
        clean = _sanitize_term(term)
        if clean:
            corpus_terms.append((clean, score))

    seed_items = build_seed_items(locale=locale, product_type=product_type, channel=channel, max_seeds=max_seeds)
    head_seeds = [term for term, seed_type in seed_items if seed_type == PlannerSeed.SeedType.HEAD]
    feature_seeds = [term for term, seed_type in seed_items if seed_type == PlannerSeed.SeedType.FEATURE]

    final_seeds = [term for term, _typ in seed_items]

    return {
        "product_type": product_type.code,
        "locale": locale.code,
        "channel": channel.code if channel else None,
        "main_label": pt_label,
        "label_fragments": label_frags,
        "synonyms": synonyms,
        "value_terms": value_terms,
        "corpus_terms": corpus_terms,
        "head_seeds": head_seeds,
        "feature_seeds": feature_seeds,
        "final_seeds": final_seeds,
        "final_seed_items": seed_items,
    }


def persist_seeds(
    *,
    locale: Locale,
    product_type: ProductType,
    channel,
    terms: Iterable[SeedTerm],
) -> List[PlannerSeed]:
    """
    Upsert PlannerSeed rows for the given scope, activate provided terms,
    and deactivate other seeds in the same scope.
    """
    activated = []
    normalized_terms = set()
    for item in terms:
        if isinstance(item, tuple):
            term, seed_type = item
        else:
            term, seed_type = item, PlannerSeed.SeedType.HEAD
        norm = _normalize(term)
        if not norm:
            continue
        normalized_terms.add(norm)
        seed, _ = PlannerSeed.objects.update_or_create(
            locale=locale,
            product_type=product_type,
            channel=channel,
            normalized_term=norm,
            defaults={
                "term": term,
                "seed_type": seed_type,
                "is_active": True,
            },
        )
        activated.append(seed)

    PlannerSeed.objects.filter(
        locale=locale,
        product_type=product_type,
        channel=channel,
    ).exclude(normalized_term__in=normalized_terms).update(is_active=False)
    return activated


def _product_type_label(locale: Locale, product_type: ProductType) -> str:
    # Prefer localized main_category if present
    main_cat = (
        ProductTypeI18n.objects.filter(product_type=product_type, locale=locale)
        .values_list("main_category", flat=True)
        .first()
    )
    main_cat = _label_head(main_cat)
    if main_cat:
        return main_cat
    label = (
        ProductTypeI18n.objects.filter(product_type=product_type, locale=locale)
        .values_list("label", flat=True)
        .first()
    )
    if label:
        return _label_head(label)
    # Do not fall back to other locales for seeds; prefer code/default_label instead of mixing languages.
    fallback_main = _label_head(product_type.main_category)
    if fallback_main:
        return fallback_main
    return _label_head(product_type.default_label) or product_type.code


def _product_type_synonyms(locale: Locale, product_type: ProductType, channel) -> List[str]:
    qs = (
        ProductTypeSynonym.objects.filter(
            product_type=product_type,
            locale=locale,
            status=SynonymStatus.APPROVED,
            is_active=True,
        )
        .filter(Q(channel=channel) | Q(channel__isnull=True))
        .order_by("-channel", "-priority", "-score")
    )
    return [row.term for row in qs]


def _attribute_value_terms(locale: Locale, product_type: ProductType, channel, limit: int = 15) -> List[str]:
    """
    Pull localized attribute value terms for products of this product_type,
    prioritizing approved synonyms (channel-first) then i18n labels.
    """
    product_ids = list(Product.objects.filter(product_type=product_type).values_list("id", flat=True)[:500])
    if not product_ids:
        return []

    allowed_attr_codes = TITLE_ELIGIBLE_ATTRS_BY_PT.get(product_type.code, set())

    pav_qs = ProductAttributeValue.objects.filter(product_id__in=product_ids).exclude(attribute_value_id__isnull=True)
    if allowed_attr_codes:
        pav_qs = pav_qs.filter(attribute__code__in=allowed_attr_codes)

    value_ids = list(pav_qs.values_list("attribute_value_id", flat=True).distinct())
    if not value_ids:
        return []

    terms: List[str] = []
    seen = set()

    def push(raw: str):
        clean = _sanitize_term(raw)
        if not clean:
            return
        norm = _normalize(clean)
        if not norm or norm in seen:
            return
        if _is_invalid_seed(norm):
            return
        terms.append(clean)
        seen.add(norm)

    fetch_n = limit * 4
    syn_qs = (
        AttributeValueSynonym.objects.filter(
            attribute_value_id__in=value_ids,
            locale=locale,
            status=AttributeValueSynonym.Status.APPROVED,
        )
        .filter(Q(channel=channel) | Q(channel__isnull=True))
        .order_by("-channel", "-score", "-updated_at")
        .values_list("term", flat=True)[:fetch_n]
    )
    for t in syn_qs:
        push(t)
        if len(terms) >= limit:
            return terms[:limit]

    label_qs = (
        AttributeValueI18n.objects.filter(attribute_value_id__in=value_ids, locale=locale)
        .values_list("label", flat=True)[:fetch_n]
    )
    for t in label_qs:
        push(t)
        if len(terms) >= limit:
            break

    return terms[:limit]


def _top_corpus_terms(locale: Locale, product_type: ProductType, limit: int = 10) -> List[Tuple[str, float]]:
    """
    Mine high-frequency head-like phrases from product.source_title/description for this product_type.
    """
    products = Product.objects.filter(product_type=product_type).values_list(
        "source_title", "source_description", "source_locale"
    )[:500]
    pt_tokens = set(_tokenize(_product_type_label(locale, product_type)))
    counter: Counter[str] = Counter()
    target_lang = _lang_prefix(locale.code)
    for title, desc, src_locale in products:
        if src_locale:
            src_lang = _lang_prefix(src_locale)
            if target_lang and src_lang and src_lang != target_lang:
                continue
        for text in (title or "", desc or ""):
            tokens = _tokenize(text)
            for phrase in _phrases(tokens):
                if _is_invalid_seed(phrase):
                    continue
                if pt_tokens and not _has_overlap(phrase, pt_tokens):
                    continue
                counter[phrase] += 1
    most_common = counter.most_common(limit)
    return [(term, float(freq)) for term, freq in most_common]


def _tokenize(text: str) -> List[str]:
    # Strip rudimentary HTML tags (e.g., <li>) that leak into source descriptions.
    cleaned = re.sub(r"<[^>]+>", " ", text or "")
    return [t.lower() for t in TOKEN_RE.findall(cleaned)]


def _phrases(tokens: List[str]) -> Iterable[str]:
    filtered = [t for t in tokens if len(t) >= 3 and t not in JUNK_STOPWORDS]
    for tok in filtered:
        yield tok
    # two-word phrases
    for i in range(len(filtered) - 1):
        phrase = f"{filtered[i]} {filtered[i+1]}"
        yield phrase
    # three-word phrases
    for i in range(len(filtered) - 2):
        phrase = f"{filtered[i]} {filtered[i+1]} {filtered[i+2]}"
        yield phrase


def _is_invalid_seed(term: str) -> bool:
    if not term:
        return True
    if len(term) > 40:
        return True
    t = term.strip().lower()
    if t in PLACEHOLDER_TERMS:
        return True
    if any(p in t for p in PLACEHOLDER_TERMS):
        return True
    if DIMENSION_RE.fullmatch(t):
        return True
    if re.fullmatch(r"\d+[xX]\d+", t):
        return True
    if _looks_like_sku_or_slug(t):
        return True
    if _looks_like_brand(term.strip()):
        return True
    word_count = len(t.split())
    if word_count > 3:
        return True
    if any(stop in t for stop in INTENT_STOPWORDS):
        return True
    if any(ch in t for ch in ["/", "\\", "|", "&"]):
        return True
    tokens = t.split()
    if all(tok in JUNK_STOPWORDS or len(tok) < 3 for tok in tokens):
        return True
    if all(tok.isdigit() for tok in tokens):
        return True
    return False


def build_seed_items(
    *,
    locale: Locale,
    product_type: ProductType,
    channel,
    max_seeds: int = 8,
    max_head: int = 4,
) -> List[tuple[str, str]]:
    """
    Build typed seed terms with a simple head/feature quota for stability.
    """
    head: List[Tuple[str, float]] = []
    feature: List[Tuple[str, float]] = []

    pt_label = _product_type_label(locale, product_type)
    pt_label_clean = _sanitize_term(pt_label)
    if pt_label_clean:
        head.append((pt_label_clean, 100.0))
        for frag in _label_fragments(pt_label, max_fragments=4):
            if frag != pt_label_clean:
                head.append((frag, 80.0))

    for term in _product_type_synonyms(locale, product_type, channel):
        clean = _sanitize_term(term)
        if clean:
            head.append((clean, 50.0))

    for term in _attribute_value_terms(locale, product_type, channel, limit=40):
        clean = _sanitize_term(term)
        if clean:
            feature.append((clean, 30.0))

    for term, score in _top_corpus_terms(locale, product_type, limit=10):
        clean = _sanitize_term(term)
        if clean:
            feature.append((clean, score))

    def _pick(items: List[Tuple[str, float]], limit: int, seen: set[str]) -> List[str]:
        chosen: List[str] = []
        for term, _score in sorted(items, key=lambda x: x[1], reverse=True):
            norm = _normalize(term)
            if not norm or norm in seen:
                continue
            if _is_invalid_seed(norm):
                continue
            chosen.append(term.strip())
            seen.add(norm)
            if len(chosen) >= limit:
                break
        return chosen

    seen: set[str] = set()
    head_limit = min(max_head, max_seeds)
    head_terms = _pick(head, head_limit, seen)
    feature_limit = max_seeds - len(head_terms)
    feature_terms = _pick(feature, feature_limit, seen)

    if not head_terms and pt_label_clean:
        head_terms = [pt_label_clean]

    return [(t, PlannerSeed.SeedType.HEAD) for t in head_terms] + [
        (t, PlannerSeed.SeedType.FEATURE) for t in feature_terms
    ]


def _has_overlap(phrase: str, pt_tokens: set[str]) -> bool:
    phrase_tokens = set(phrase.split())
    return bool(phrase_tokens & pt_tokens)


def _normalize(term: str) -> str:
    return re.sub(r"\s+", " ", term.strip().lower())


def _lang_prefix(locale_code: str) -> str:
    return (locale_code or "").split("-")[0].lower()


def _sanitize_term(term: str) -> str:
    """
    Reduce noisy labels/synonyms by splitting on separators and keeping a short, meaningful fragment.
    """
    if not term:
        return ""
    fragments = re.split(r"[\\/&|,;>]+", term)
    cleaned = []
    for frag in fragments:
        frag = frag.strip()
        if not frag:
            continue
        frag = re.sub(r"\s+", " ", frag)
        if len(frag.split()) > 4:
            continue
        if len(frag) > 40:
            continue
        if _is_invalid_seed(frag.lower()):
            continue
        cleaned.append(frag)
    # Prefer the first acceptable fragment; fallback to original if nothing passes
    if cleaned:
        return cleaned[0]
    # Last resort: if original term is short enough and not invalid, keep it
    term_norm = re.sub(r"\s+", " ", term.strip())
    return "" if _is_invalid_seed(term_norm.lower()) else term_norm


def _label_fragments(label: str, max_fragments: int = 3) -> List[str]:
    if not label:
        return []
    parts = re.split(r"[\\/&,;>]+", label)
    frags: List[str] = []
    seen = set()
    for part in parts:
        part = part.strip()
        if not part:
            continue
        part = part.replace("-", " ")
        for chunk in re.split(r"\s{2,}", part):
            chunk = re.sub(r"\s+", " ", chunk.strip())
            if not chunk or len(chunk) > 40 or len(chunk.split()) > 3:
                continue
            if _is_invalid_seed(chunk.lower()):
                continue
            norm = _normalize(chunk)
            if norm in seen:
                continue
            frags.append(chunk)
            seen.add(norm)
            if len(frags) >= max_fragments:
                return frags
    return frags


def _label_head(label: str) -> str:
    """
    Prefer the shortest meaningful segment from a path-like label (split on /, >, &, commas).
    """
    if not label:
        return ""
    parts = [p.strip() for p in re.split(r"[\\/&,;>]+", label) if p.strip()]
    if not parts:
        return ""
    # Choose the shortest acceptable fragment
    parts = sorted(parts, key=len)
    for part in parts:
        part_norm = re.sub(r"\s+", " ", part)
        if part_norm and len(part_norm) <= 40 and len(part_norm.split()) <= 4 and not _is_invalid_seed(part_norm.lower()):
            return part_norm
    # fallback to original cleaned
    fallback = re.sub(r"\s+", " ", label.strip())
    return "" if _is_invalid_seed(fallback.lower()) else fallback
