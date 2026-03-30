# Keyword Mapping Guide

How keywords are mapped to products and how head/hook terms are extracted and explained.

---

## Overview

The keyword mapping pipeline has two stages:

1. **Rules-based mapping** (`/map/` endpoint) — fast, deterministic, matches keywords to attribute values by text/enum overlap. Source label: `enum_map`.
2. **AI mapping** (`/persist-mappings/` with `use_llm=true`) — sends unmatched keywords to an LLM with full product context. Source label: `pav_text_llm`.

When both run, **AI results overwrite rules-based rows** for the same `(product, keyword, run)`. Rules rows for keywords the AI skipped are kept as a fallback.

---

## Stage 1: Rules-based mapping

Called via `POST keywords/planner-run/<run_id>/map/`.

### What it does
- Builds an `AttributeMap` for every keyword in the run by looking for text overlap between keyword phrases and attribute value labels / codes.
- Detects enum matches (e.g. keyword "rouge" → `couleur = rouge`) and numeric matches (e.g. keyword "120 cm" → `profondeur = 120 cm`).

### Numeric matching rule
Bare numbers are only matched when the attribute has **no unit**. If the attribute has a unit (e.g. `profondeur = 120 cm`), the keyword must contain the number **with the unit** (`"120 cm"` or `"120cm"`) — matching bare `"120"` alone is rejected to avoid false positives.

### Size and marketplace filtering
Attributes are detected as "size" or "marketplace name" via **language-agnostic pattern matching** (not hardcoded codes). The patterns cover FR / EN / DE / ES / IT / PT:

- **Size prefixes**: `longueur`, `largeur`, `hauteur`, `profondeur`, `epaisseur`, `length`, `width`, `height`, `depth`, `thickness`, `breite`, `höhe`, `länge`, `tiefe`, `ancho`, `alto`, `largo`, `profundo`, `larghezza`, `altezza`, `lunghezza`, …
- **Size suffixes**: `_cm`, `_mm`, `_m`, `_inch`, `_in`, `_px`
- **Non-hook prefixes**: `warranty`, `garantie`, `garantia`, `stock`, `bestand`, `weight`, `gewicht`, `poids`, `price`, `preis`, `prix`, `rating`, `review`, …
- **Non-hook suffixes**: `_qty`, `_menge`, `_kg`, `_jahre`, `_years`, `_ans`, …

Pass `ignore_size_and_marketplace=true` to `persist-mappings` to skip these attributes entirely.

---

## Stage 2: AI mapping

Called via `POST keywords/planner-run/<run_id>/persist-mappings/` with `use_llm=true`.

### What the AI receives
- Full product attribute sheet (all `ProductAttributeValue` rows with labels and values).
- All keywords from the run that are not already text-matched.
- Optional instructions via `focus_on` / `ignore` / `focus_head_terms` / `focus_hook_terms`.

### What the AI returns
For each keyword: whether it matches the product and, if so, which attribute/value it corresponds to, with a confidence score and reason.

### Persistence
Results are stored as `ProductKeywordMap` rows with `source=pav_text_llm`. Any existing `enum_map` rows for the same `(product, keyword, run)` are deleted first so AI is the single source of truth for those keywords.

---

## Head and hook term extraction

Called via `GET keywords/planner-run/<run_id>/suggested-terms/`.

### Classification logic (`kw/services/term_extraction.py`)
Keywords in `ProductKeywordMap` are classified as **head** or **hook**:

- **Head terms** — high-volume, short, generic (1-2 words). These define what the product *is*.
- **Hook terms** — longer, specific, lower volume. These address a specific search intent (dimension, use-case, material, etc.).

### AI reasons (`use_ai_reason=1`)
When this param is passed, a single AI call is made for all terms in the response. Each term gets a `reason` field explaining *why* it was classified that way:

- Head terms always get a reason.
- Hook terms already explained by the product mapping step (`pav_text_llm` source) keep their existing reason; only terms without one get a new AI reason.

**Example response item:**
```json
{
  "keyword": "table basse 120 cm",
  "vol": 1900,
  "source": "pav_text_llm",
  "reason": "Matches product attribute profondeur=120cm — the dimension appears directly in the search phrase."
}
```

### AI meanings (`use_ai_meaning=1`)
Returns a `meaning` field with a plain-language description of what a shopper searching that keyword is looking for. Useful for editorial review.

---

## Template attribute order proposal

Called via `GET keywords/planner-run/<run_id>/propose-template/`.

Uses the existing `ProductKeywordMap` data (no extra AI cost for the base case) to rank product attributes by total search volume of mapped keywords.

Optional `use_ai=1` sends the volume-ranked list plus:
- Product type label / category
- Run locale (e.g. `fr-FR`, `de-DE`)
- Top 10 actual search queries from the run

The AI reorders attributes semantically for the product category and locale, writing reasons in the locale's language. Works for any language and any product type — the AI adapts based on shopper queries and locale conventions, not hardcoded rules.

---

## Typical workflow

```
1. Import keywords CSV
   POST keywords/planner-run/import-csv/

2. (Optional) Run rules-based mapping for a quick first pass
   POST keywords/planner-run/<run_id>/map/

3. Run AI mapping — this overwrites any rules rows for matched keywords
   POST keywords/planner-run/<run_id>/persist-mappings/
   { "use_llm": true, "skip_enum_maps": true }

4. Review product-level maps
   GET keywords/planner-run/<run_id>/product-maps/

5. Extract head/hook terms with AI explanations
   GET keywords/planner-run/<run_id>/suggested-terms/?use_ai_reason=1

6. (Optional) Get AI-suggested attribute order for title template
   GET keywords/planner-run/<run_id>/propose-template/?use_ai=1
```

---

## Code locations

| Concern | File |
|---------|------|
| Rules mapping | `kw/services/mapping_service.py` → `run_rules_mapping()` |
| AI mapping | `kw/services/product_keyword_mapper.py` → `persist_product_keyword_maps()` |
| Size/non-hook detection | `kw/services/product_keyword_mapper.py` → `_is_size_attribute()`, `_is_non_hook_attribute()` |
| Term extraction & classification | `kw/services/term_extraction.py` |
| AI term reasons | `kw/services/term_extraction.py` → `generate_term_reasons()` |
| AI keyword meanings | `kw/services/term_extraction.py` → `generate_keyword_meanings()` |
| API views | `api/v1/views/keywords.py` |
