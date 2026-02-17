# Locale packs

Per-language config: synonyms, stopwords, unit variants, morphology.

## Intended contents (when implemented)

- `de/` — German: synonyms per PT and attribute values, stopwords/connectors, units (cm, mm, …)
- `fr/` — French
- `en/` — English
- `es/`, `it/`, `nl/`, `pl/` — later

Each pack drives: term → canonical concept, unit normalization, banned tokens.

**Stopwords (connectors):** Multi-lingual stopwords used in keyword→product matching live in **`kw/stopwords.py`** (`STOPWORDS_BY_LANG`). One list per language code (de, en, fr, it, es, nl, pl, …); the mapper uses the union of all. Add a language by adding a key and list—no code changes elsewhere.
