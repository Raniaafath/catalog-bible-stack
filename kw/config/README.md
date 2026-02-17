# Keyword extraction & mapping config (config-first)

This folder holds **config-driven** definitions for the global extraction framework. Add new product types or languages via YAML/JSON, not code changes.

## Structure

| Folder | Purpose | Expected format |
|--------|---------|------------------|
| `ontology/` | Product types, canonical attributes per PT, value domains | YAML schemas (see design) |
| `locales/` | Per-language synonyms, stopwords, units, morphology | One pack per locale (DE, FR, EN, …) |
| `rules/` | Regex patterns, mapping rules, per-attribute policies | YAML |
| `scoring/` | Confidence thresholds, auto-apply / review / reject policies | YAML |

## Design reference

See **docs/EXTRACTION_FRAMEWORK.md** for:

- Universal pipeline (normalize → language → intent → entity extraction → attribute mapping → scoring → buckets)
- Global ontology, locale packs, rule engine, ML layer
- Data model (locale_lexicon, regex_patterns, mapping_rules, scoring_policies, human_review_queue)
- Confidence policy and “stupid mapping” guardrails

## Current state

- Placeholder structure only. Implementation will load these configs and drive the pipeline.
- When YAML schemas are added, this README will link to schema docs.
