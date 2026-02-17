"""
Multi-lingual connector/stop words for keyword→product matching.

Words in these lists are not used as the sole match evidence (e.g. "oder", "zum"
should not create a mapping). One entry per language code; the mapper uses the
union of all languages so the same logic works for any locale.

To add a language: add a key (e.g. "it", "es") and a list of normalized tokens.
"""
from __future__ import annotations

from typing import FrozenSet

# Language code (ISO 639-1 or 639-2) → list of normalized stopwords (lowercase, no spaces).
# Add new languages here; no code changes needed in the mapper.
STOPWORDS_BY_LANG: dict[str, list[str]] = {
    "de": [
        "oder", "zum", "zur", "und", "mit", "ohne", "für", "auf", "aus", "bei", "nach", "von",
        "der", "die", "das", "den", "dem", "des", "ein", "eine", "einer",
    ],
    "en": [
        "and", "or", "for", "with", "without", "the", "to", "in", "on", "by", "at",
    ],
    "fr": [
        "et", "ou", "pour", "avec", "sans", "sur", "dans", "par", "le", "la", "les", "un", "une",
    ],
    "it": [
        "e", "ed", "o", "per", "con", "senza", "il", "la", "i", "le", "un", "uno", "una", "di", "da", "in", "su",
    ],
    "es": [
        "y", "o", "para", "con", "sin", "el", "la", "los", "las", "un", "una", "de", "en", "por",
    ],
    "nl": [
        "en", "of", "voor", "met", "zonder", "de", "het", "een", "van", "in", "op",
    ],
    "pl": [
        "i", "oraz", "lub", "dla", "z", "bez", "w", "na", "do", "od",
    ],
}

_cached_union: FrozenSet[str] | None = None


def get_match_stopwords() -> FrozenSet[str]:
    """Return the union of all per-language stopwords (multi-lingual, not locale-specific)."""
    global _cached_union
    if _cached_union is None:
        all_words: set[str] = set()
        for words in STOPWORDS_BY_LANG.values():
            all_words.update(w.strip().lower() for w in words if w)
        _cached_union = frozenset(all_words)
    return _cached_union
