# Global extraction framework (scalable design)

**Goal:** One universal pipeline for keyword/text extraction and attribute mapping—all languages, all product types—no product-specific hacks. Config-first so new categories or languages don’t require code rewrites.

---

## 1. Universal pipeline

1. **Normalize text** — lowercase, unicode NFKC, punctuation, tokenization
2. **Language detect** — or use marketplace locale
3. **Intent classification** — which product type(s)?
4. **Entity extraction** — dimensions, colors, materials, shape, installation, etc.
5. **Attribute mapping** — only from allowed schema for detected product type
6. **Scoring + conflict resolution**
7. **Output buckets** — auto-apply / review / reject

---

## 2. Core abstraction layers

### Global ontology

- **Product types (PT):** e.g. `shower_tray`, `shower_enclosure`, `bathtub`
- **Canonical attributes per PT:** e.g. `length_cm`, `width_cm`, `material`, `shape`, `installation`
- **Value domains per attribute:** enum + free-text rules

### Locale packs (DE / FR / EN / ES / IT / …)

- Synonyms per PT and attribute values
- Stopwords / connectors
- Unit variants (`cm`, `mm`, `po`, `inch`)
- Morphology / abbreviations

### Rule engine

- Reusable regex extractors (dimensions, units, quantities)
- Per-attribute matching policies
- Confidence thresholds

### ML layer (optional)

- Intent model (multi-label)
- NER for hard cases
- Fallback when lexicon/rules are insufficient

---

## 3. Data model to keep / add

| Model / concept        | Role |
|------------------------|------|
| `product_types`       | Already in catalog |
| `attributes`           | Already in catalog |
| `attribute_values`     | Already in catalog |
| `locale_lexicon`       | term → canonical concept |
| `regex_patterns`       | reusable extractors |
| `mapping_rules`        | per-attribute policies |
| `scoring_policies`     | global thresholds |
| `keyword_processing_log` | audit trail |
| `human_review_queue`   | medium-confidence items |

---

## 4. Confidence policy (global)

- **High (≥ 0.90):** auto-map
- **Medium (0.70–0.89):** review queue
- **Low (&lt; 0.70):** keep keyword only, no mapping
- **Hard fail** if: intent mismatch, cross-category contamination, impossible dimension patterns

---

## 5. Prevent “stupid mapping” globally

- Attribute allowlist by product type
- Banned token mapping (`oder`, `zum`, `avec`, `for`, etc.)
- Multi-entity guardrails (comparison keywords don’t auto-map)
- Dimension parser: validate both sides and unit consistency
- Conflict detector: e.g. `material=acrylic` + `material=steel` ⇒ multi-value intent or review

---

## 6. Rollout plan

1. Build canonical ontology for top 20 product types
2. Add locale packs for DE / FR / EN first
3. Implement universal regex + scoring
4. Start with “auto-map only high confidence”
5. Measure precision/recall by category/language
6. Expand to ES / IT / NL / PL + more categories

---

## 7. Config location (this repo)

- **Ontology:** `kw/config/ontology/` (product types, canonical attributes, value domains)
- **Locale packs:** `kw/config/locales/` (per-language synonyms, stopwords, units)
- **Rules:** `kw/config/rules/` (regex patterns, mapping rules)
- **Scoring:** `kw/config/scoring/` (thresholds, policies)
- **Review workflow:** config + `human_review_queue` model

See `kw/config/README.md` and the YAML schemas in each subfolder when added.

---

## See also

- [ATTRIBUTE_ONE_DIMENSION.md](ATTRIBUTE_ONE_DIMENSION.md) — one attribute = one semantic dimension
- [GROUPING_AND_MARKETPLACE_AXES.md](GROUPING_AND_MARKETPLACE_AXES.md) — product family vs listing group, axes
