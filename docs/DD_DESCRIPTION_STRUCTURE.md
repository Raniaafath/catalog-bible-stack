# Recommended structure for “DD description” per variant

This document defines the recommended structure for detailed product descriptions (DD) that are generated per variant, with a clear split between product-level narrative, variant-specific deltas, user instructions, and channel-specific output.

---

## 1) Parent description block (product-level, reusable)

Use this for facts **common to all variants**:

- What the product is
- Core benefits
- Material family / use case
- Installation/compatibility basics
- What’s included

This becomes your stable **“base narrative”**.

**Mapping (codebase):** `content.ContentBlock` with `block_type` e.g. `parent_description` or `base_narrative`, scoped by `product` + `locale`. One or more blocks per product/locale; `sort_order` for ordering.

---

## 2) Variant delta block (auto-filled from attributes)

Per variant, inject **only what changes**:

- Dimensions
- Color/finish
- Material subtype
- Thickness/weight
- Pack quantity
- Compatibility detail

This avoids duplicate/contradictory content and keeps each variant precise. It aligns with variant logic in Google feeds (`item_group_id` + per-variant attributes such as color/size/material/pattern).

**Mapping (codebase):** Built from `catalog.ProductAttributeValue` (and `content.ProductAttributeValueI18n` for translated values) for the variant. No separate “delta block” storage required; generated at output time from variant attributes.

---

## Description generation from attribute values / Showing attribute values used per variant

Description text is built from the **variant delta** (attribute values) for the selected locale and channel; it can later be combined with the parent block and user instructions.

The system exposes **which attribute values are used for each variant** so users can verify inputs before generating. For each variant, show a table of:

- **Attribute** (code)
- **Value** (display value used in the description)
- **Source** (product-level vs variant-level, and translation source when relevant)

This list is returned by the backend as a **features** list per variant. Use the content preview API with `include_descriptions=True` (POST `/api/v1/content/preview/` with `variant_id`, `locale_code`, `channel_code`). The response includes `features`: an array of `{ attribute_code, value, source, attribute_value_id }` that was used to build the description (and bullets). The same features drive `_build_description` and `_build_bullets` in `pub.services.content_generation`.

---

## 3) User instruction block (free text for your team)

A dedicated section for **editorial instructions** (e.g. “Editorial instructions / Consignes rédactionnelles”).

**Split into:**

| Area | Purpose |
|------|--------|
| **Hard constraints** | Must include / must avoid |
| **Soft preferences** | Tone, style, CTA intensity |

**Example fields:**

- Must include keywords
- Must avoid claims
- Tone (technical / premium / friendly)
- Audience (B2C DIY / pro installer)
- Length target
- Language/locale rules (FR/DE/EN)

**Mapping (codebase):** New block type on `ContentBlock` (e.g. `editorial_instructions`) or a dedicated model (e.g. `ProductDescriptionInstructions`) with product + locale + optional channel, storing structured fields and/or free text.

---

## 4) Channel output block (marketplace-aware format)

Generate **differently per channel**:

- Shopify PDP
- Google feed description
- Marketplace bullets (Leroy/Mano etc.)
- Meta description / short snippet

Feed and SEO channels have different parsing and length constraints. Google supports structured product/variant markup (`ProductGroup`, `variesBy`, `hasVariant`) for clearer grouping in Search.

**Mapping (codebase):** Output format is determined by **channel** (and possibly a “format” or “template” key). Same inputs (parent block + variant delta + user instructions) are passed to a generator that emits channel-specific text/structure. Store outputs in generation runs or in channel-specific fields if needed.

---

## Form design (practical)

**Suggested UI layout:**

1. **Locked product facts** (read-only from catalog)
2. **Variant attributes** (auto-loaded from variant record)
3. **User instructions** (editable textarea + structured controls)
4. **Generate**
5. **Preview + QA flags**
6. **Approve / Regenerate / Manual edit**

---

## Notes

- **Shopify:** Variant options are capped (3 option axes). Extra descriptive detail should live in metafields/custom attributes rather than in option names.
- **Google:** Use `item_group_id` for the product family and per-variant attributes for the delta so grouping and variant differentiation stay clear in Search and feeds.

---

## Summary table

| Block | Scope | Source | Use |
|-------|--------|--------|-----|
| Parent description | Product + locale | ContentBlock (base narrative) | Stable text shared by all variants |
| Variant delta | Variant | ProductAttributeValue / I18n | Auto-injected variant-specific facts |
| User instructions | Product + locale (optional channel) | New block or model | Constraints and preferences for generation |
| Channel output | Variant + channel + locale | Generated from above | Shopify PDP, Google feed, bullets, meta, etc. |
