# Title generation: flow and translation logic

This doc explains **how titles are generated** (from API to stored title) and **how the chosen language is applied** to attribute values. See also [TITLE_GENERATION_SCRIPT.md](TITLE_GENERATION_SCRIPT.md) for head/hook/axes behaviour.

## End-to-end flow

1. **API**  
   `POST /api/v1/channel-listings/{id}/generate-titles/` with body `{ "locale_code": "de-DE", "template_id": 7 }`.  
   - `locale_code` = **target language** for the generated titles (and for attribute value translations).  
   - `template_id` = optional; if provided, that template is used (must match listing’s product_type, channel, and the same locale).

2. **Service**  
   - `generate_titles_for_listing(listing_id, locale_code, template_id, …)` builds a `TitleGenerationRequest` and calls `generate_titles(request)`.  
   - `generate_titles()` loads locale, channel, variants; for each variant calls `save_generation(…, template_id=request.template_id)`.

3. **Policy and template**  
   - `save_generation()` resolves the channel/locale policy (e.g. auto vs review).  
   - It calls `render_title(…, template_id=template_id)`.

4. **Template selection** (in `render_title`)  
   - If `template_id` is set: load that template and require it to be active and to match the variant’s product_type, locale, and channel. If not found or mismatch, raise.  
   - If `template_id` is not set: take the **latest active** template for (product_type, locale, channel) by `-version`, `-id`.

5. **Resolving each template part**  
   For each part (head term, hook term, literal, axis attribute, attribute value):  
   - Head/hook: from selection or from product-type keywords / saved terms.  
   - Literal: fixed text.  
   - Axis attribute / Attribute value: value comes from the variant’s (or product’s) `ProductAttributeValue`; the **display label** is resolved with the **translation logic** below (using the **requested locale**).

6. **Final title and storage**  
   Resolved parts are concatenated and cleaned in `_clean_title_parts()`. Uniqueness is enforced in `_reserve_unique_title()`. Then a `GenerationRun` and `GenerationOutput` are created with the title text.

So: **template** defines *which* attributes (and head/hook/literals) appear; **locale_code** defines *in which language* attribute values are shown.

---

## How attribute values get their language (translation lookup)

The requested **locale** (e.g. `de-DE`) is the one chosen in the UI as “Target Language”. For each attribute value that appears in the title, the renderer resolves a **label** in this order:

1. **ProductAttributeValueI18n** (per-PAV, per locale)  
   If the variant’s `ProductAttributeValue` has a row in `ProductAttributeValueI18n` for this locale, that `value_text` is used.  
   → Best for per-variant overrides or free-text attributes.

2. **AttributeValueSynonym** (approved, for channel/locale)  
   If there is an approved synonym for this attribute value and locale (and optionally channel), that term is used.

3. **AttributeValueI18n** (per attribute value, per locale)  
   If the attribute value (enum) has a row in `AttributeValueI18n` for this locale, that `label` is used.  
   → One translation per enum value; applies to **all** variants that use that value. This is the main source when you run “Product attribute values” translation and then backfill (or when the task syncs to `AttributeValueI18n`).

4. **Fallback**  
   If none of the above exist, the **raw** value is used: `AttributeValue.code` or `ProductAttributeValue.value_text` (often the source language, e.g. French).

So: **template** = which attributes; **locale** = which language; **Translations** (and backfill) = provide the strings so the renderer does not fall back to the raw value.

---

## Where the code lives

| Step | Where |
|------|--------|
| API | `api/v1/views/pub.py` → `ChannelListingGenerateTitlesView` |
| Listing → request | `catalog/services/channel_listings.py` → `generate_titles_for_listing()` |
| Per-variant generation | `pub/services/generation_service.py` → `generate_titles()`, `save_generation()` |
| Template selection | `pub/services/title_renderer.py` → `render_title()` (uses `template_id` or latest active) |
| Part resolution | `render_title()` loop; axis/attribute value → `_resolve_axis_attribute()`, `_resolve_attribute_value()` |
| Label for one PAV | `_stringify_attribute_value()` (uses `pav_i18n_texts`, synonyms, `i18n_labels`, then raw) |
| Load i18n maps | `_load_i18n_labels()` (AttributeValueI18n), `_load_pav_i18n_texts()` (ProductAttributeValueI18n) |
| Uniqueness | `_reserve_unique_title()` |

---

## Wrong language in titles

- **Cause:** For the chosen target locale there is no translation in `AttributeValueI18n` (or `ProductAttributeValueI18n` for that PAV), so the renderer falls back to the raw code/text (e.g. French).
- **Fix:**  
  1. Add (or run) translations for that locale in **Translations** (Attribute values / Product attribute values).  
  2. For enum values, run the **backfill** so existing `ProductAttributeValueI18n` rows are synced to `AttributeValueI18n`:  
     `python manage.py backfill_attribute_value_i18n_from_pav` (optionally `--locale de-DE`).  
  3. Regenerate titles for that listing and locale.

---

## Strict locale (no fallback)

If `TITLE_STRICT_LOCALE` is `True` (default), the renderer does **not** fall back to another locale (e.g. default/source) when loading `AttributeValueI18n` or `ProductAttributeValueI18n`. Only the requested locale is used. So the “wrong language” is either the requested locale (if you chose the wrong one) or the raw value when no translation exists for that locale.
