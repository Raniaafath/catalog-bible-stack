# Keyword Extraction & Mapping Framework

How keywords are extracted from search data, mapped to product attributes, and turned into head/hook terms for title generation.

---

## Pipeline overview

```
1. Import keywords          CSV upload or Google Ads API
2. Parse keywords           Split into phrases, normalize
3. Rules-based mapping      Text/enum overlap → AttributeMap (fast, free)
4. AI mapping               LLM per-product → ProductKeywordMap (pav_text_llm)
5. Extract terms            Classify mapped keywords as head or hook
6. Review & approve         User saves head/hook terms per product/locale
7. Title generation         Terms feed into title template rendering
```

---

## Stage 1-2: Import and parse

Keywords are imported via `POST /keywords/planner-run/import-csv/` or seeded from Google Ads (`PlannerSeed`). Each keyword is parsed into normalized phrases by `kw/services/csv_import.py` and stored in `KeywordParse`.

---

## Stage 3: Rules-based mapping

`POST /keywords/planner-run/{id}/map/` → `kw/services/mapping_service.py`

Matches keywords to attribute values by text overlap (phrase match). Fast and free but limited — can miss context-dependent mappings and can produce false positives on bare numbers. Stored as `AttributeMap` rows with source `enum_map`.

---

## Stage 4: AI mapping

`POST /keywords/planner-run/{id}/persist-mappings/` with `use_llm=true` → `kw/services/product_keyword_mapper.py`

Sends unmatched keywords to an LLM with full product context (all attribute values). AI decides per-product which keywords are relevant and which attribute they correspond to. Stored as `ProductKeywordMap` rows with source `pav_text_llm`.

**AI overwrites rules:** when AI maps a keyword, any existing `enum_map` row for the same `(product, keyword, run)` is deleted. Rules rows for keywords the AI skipped are kept as fallback.

**Language-agnostic filters** — attributes are excluded from mapping if their code matches:
- Size/dimension prefixes: `longueur`, `largeur`, `breite`, `ancho`, `length`, `width`, …
- Size suffixes: `_cm`, `_mm`, `_inch`, …
- Operational prefixes: `warranty`, `garantie`, `stock`, `price`, `weight`, …
- Operational suffixes: `_qty`, `_kg`, `_jahre`, `_years`, …

**Numeric matching rule:** bare numbers (e.g. `"30"`) are only matched when the attribute has no unit. If the attribute value includes a unit (`profondeur = 30 cm`), the keyword must contain the number with the unit (`"30 cm"` or `"30cm"`).

---

## Stage 5: Extract head and hook terms

`GET /keywords/planner-run/{id}/suggested-terms/` → `kw/services/term_extraction.py`

**Head terms** — general product-type category words (e.g. `"Duschwanne"`, `"table basse"`). Sourced from `product_label`, `product_category`, `product_i18n_title` match kinds. One set per run/product-type.

**Hook terms** — product differentiators (colour, material, shape, finish). Sourced from `pav_text_llm`, `pav_text`, `attr_value_label` match kinds. One set per product.

Both can be enriched with AI explanations:
- `?use_ai_reason=1` — why each term is a good head/hook term
- `?use_ai_meaning=1` — plain-English meaning of each head term

---

## Stage 6: Approve and save

- **Head terms:** `POST /api/v1/product-types/{id}/head-terms/` → `ProductTypeSynonym`
- **Hook terms:** `POST /api/v1/products/{id}/hook-terms/` → `ProductHookTerm`

Both are scoped to locale and optionally channel. Approved terms are used by the title renderer.

---

## Stage 7: Title generation

The title renderer (`pub/services/title_renderer.py`) resolves `HEAD_TERM` and `HOOK_TERM` template parts from saved `ProductTypeSynonym` and `ProductHookTerm` rows for the requested locale + channel.

---

## Code locations

| Concern | File |
|---------|------|
| CSV import | `kw/services/csv_import.py` |
| Rules mapping | `kw/services/mapping_service.py` |
| AI mapping + persist | `kw/services/product_keyword_mapper.py` |
| Size/non-hook detection | `kw/services/product_keyword_mapper.py` → `_is_size_attribute()`, `_is_non_hook_attribute()` |
| Term extraction | `kw/services/term_extraction.py` |
| AI term reasons/meanings | `kw/services/term_extraction.py` → `generate_term_reasons()`, `generate_head_term_meanings_en()` |
| API views | `api/v1/views/keywords.py` |

See also: [KEYWORD_MAPPING_GUIDE.md](KEYWORD_MAPPING_GUIDE.md) for a more detailed walkthrough.
