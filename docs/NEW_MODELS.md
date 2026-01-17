# Workflow Data Model (Parent + Variants)

This document aligns the product import and content workflow with the current Django apps. It highlights which models already exist and which still need to be added or extended.

---

## Core catalog (existing)

File: `catalog/models.py`

- `Product` (parent): base title/description live here (clean, non-variant).
- `Variant` (child SKU): per-variant axis values; `axis_signature` helps uniqueness.
- `ProductVariantAxis`: stores the variation axis attributes (e.g., Color, Size) for a parent.
- `ProductAttributeValue`: stores attribute values on either product or variant.
- `ProductType`, `Attribute`, `AttributeValue`: the taxonomy + attribute universe.

Key decision: store one base title per `Product`, and append axis values only in export/generation templates.

---

## Import + normalize (new)

File: `importer/models.py` (new app)

### `CategoryBatch`
Groups a single import batch within a category/product type.

- `product_type` (FK to `catalog.ProductType`)
- `source_locale`, `source_supplier`
- `status` (draft/processing/completed/failed)
- `row_count`, `products_created`, `variants_created`
- `created_at`, `completed_at`

### `ProductImport`
Tracks the uploaded file and parsing status.

- `category_batch` (FK to `CategoryBatch`, nullable)
- `file_name`, `file_path`, `file_size`
- `status` (pending/parsing/validating/ready/processing/completed/failed)
- `detected_columns`, `column_mappings`
- `parent_key_column` (e.g., `product_parent_id`)
- `variant_key_column` (e.g., `sku` or `variant_id`)
- `axis_columns` (list of column names for axes like color/size)
- `validation_errors`, `error_log`, `preview_data`
- `created_at`, `updated_at`, `started_at`, `completed_at`

### `ImportRow`
Raw + parsed row tracking for preview/validation.

- `import_file` (FK to `ProductImport`)
- `row_number`, `status` (pending/valid/invalid/processed/error)
- `raw_data`, `parsed_data`
- `validation_errors`
- `created_product_id`, `created_variant_id`
- `processed_at`

### `AttributeMapping`
Column-to-attribute mapping for import.

- `import_file` (FK to `ProductImport`)
- `file_column`
- `attribute` (FK to `catalog.Attribute`)
- `transform_rule`, `default_value`
- Unique on (`import_file`, `file_column`)

---

## Attribute mapping + axis values (existing)

Files: `catalog/models.py`, `content/models.py`

- `ProductVariantAxis` marks which attributes are axes per parent product.
- Variant axis values live in `ProductAttributeValue` (variant-scoped).
- Non-axis attributes can be stored at product or variant scope.
- Localized attribute values in `ProductAttributeValueI18n` (content app).

---

## Translation (existing, plus small extensions)

File: `content/models.py`

- `ProductI18n`: localized product titles/descriptions.
- `ProductAttributeValueI18n`: localized attribute values.
- `TranslationTask`: batch translation queue (scope + target ids).

Recommended additions for "lock" behavior:

- Add `is_locked`, `locked_by`, `locked_at` to `ProductI18n`.
- Add `is_locked`, `locked_by`, `locked_at` to `ProductAttributeValueI18n`.

---

## Keyword planner + metrics (existing)

File: `kw/models.py`

- `PlannerRun`: one Google Ads Keyword Planner run (locale, channel, product_type).
- `PlannerRunSeed`: seed terms for the run.
- `PlannerRunKeyword`: keywords + metrics for the run.
- `Metric`: time series metrics per keyword (optional).

---

## Keyword mapping + candidate selection (existing)

File: `kw/models.py`

- `ProductKeywordMap`: keyword-to-product map with confidence, source, evidence.
- `AttributeMap`: keyword-to-attribute/value mapping (used by mapper).
- `Candidate`: HEAD/HOOK/supporting candidates with status.

Use `status` fields as review/lock signals for mappings and candidates.

---

## Head/Hook selection (existing)

File: `pub/models.py`

- `TitleSelection`: stores selected head/hook terms per product/variant/locale/channel.
- `Approval`: optional generic approval record (if you want a lock gate).

---

## Template builder (existing)

File: `pub/models.py`

- `Template`: scoped by product_type, locale, channel, kind.
- `TemplatePart`: ordered template slots.
  - `part_type="axis_attribute"` covers `{AXIS_VALUE}` placement.
  - `part_type="keyword"` covers head/hook/supporting keywords.

---

## Generation (existing)

File: `pub/models.py`

- `GenerationRun`: generation attempt for product/variant using a template.
- `GenerationOutput`: generated titles/descriptions with keyword metadata.
- `GenerationBatch`, `GenerationBatchItem`: batch orchestration + status.

---

## Export (existing)

File: `pub/models.py`

- `ExportProfile`: channel-specific export template (columns/options).
- `ExportJob`: queued export run and output file.

---

## Relationship summary

```
ProductType
  ├── Product
  │   ├── Variant
  │   ├── ProductVariantAxis (axis attributes)
  │   └── ProductAttributeValue (product or variant scope)
  └── Template (per locale/channel/kind)

ProductImport
  ├── ImportRow
  └── AttributeMapping

TranslationTask
  ├── ProductI18n
  └── ProductAttributeValueI18n

PlannerRun
  ├── PlannerRunKeyword
  ├── ProductKeywordMap
  └── Candidate

GenerationRun
  ├── GenerationOutput
  └── TitleSelection

ExportProfile
  └── ExportJob
```
