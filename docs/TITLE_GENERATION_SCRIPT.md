# Title generation script: how it works

Generated titles are built by **one head term + one hook term + template parts** (literals and variation axes). The code lives in `pub/services/title_renderer.py` and is used when you click **Generate Titles** on a listing.

## Flow

1. **Template**  
   The active title template for the listing’s product type, channel, and locale defines the **order** of parts, e.g.:
   - Head term → Literal (e.g. `" - "`) → Hook term → Axis attribute → Axis attribute

2. **Resolving each part**
   - **Head term**: Exactly **one** term. From `TitleSelection` if approved, otherwise from `_resolve_head_term()` (product type synonyms / keyword metrics). One chosen head is used for the whole product.
   - **Hook term**: Exactly **one** term. From `TitleSelection` if set, otherwise from `_resolve_hook_term()` (saved `ProductHookTerm` first, then keyword maps). Optionally, tokens that match head terms are stripped from the hook so you don’t get “head + head” (e.g. “duschtasse” + “duschwanne”).
   - **Literal**: Fixed string from the template (e.g. `" - "`).
   - **Axis attribute**: Value(s) for the variant’s variation axes (e.g. size, colour, finish), from `_resolve_axis_attribute()`.

3. **Final title**  
   Resolved parts are concatenated (with dedupe) in `_clean_title_parts()` and stored. Uniqueness is enforced in `_reserve_unique_title()`.

So in practice: **one chosen head + one chosen hook + then attributes (axes)**.

## Why you see “LATE”, “OOTH”, “LATE-791”

Those come from **uniqueness handling**, not from the main title formula.

If the **base** title is the same for several variants (e.g. “duschtasse duschwanne steinoptik” for all because there are no axis parts or they’re empty), the system must still store a **unique** title per variant. It then tries:

1. Use the base title as-is.
2. If that would duplicate an existing title: append the **last 4 alphanumeric characters of the SKU** (e.g. from `…SLATE` → `LATE`, from `…SMOOTH` → `OOTH`).
3. If still duplicate: append `{suffix}-{variant_id}` (e.g. `LATE-791`).

So **“LATE” / “OOTH” / “LATE-791” are added only when the base title is not unique.**

**Fix:** Add the **variation axes** (e.g. size, colour, finish) as parts in your title template. Then each variant gets a different base title (e.g. “duschtasse steinoptik 120x90 WH SLATE”) and the system usually won’t need to append the SKU suffix.

## Why both “duschtasse” and “duschwanne” appear

The script uses **one** head and **one** hook. If you see both “duschtasse” and “duschwanne” in the same title, it usually means:

- The **head** is one of them (e.g. “duschtasse”).
- The **hook** you saved is “duschwanne steinoptik”, so “duschwanne” is coming from the hook, not from a second head.

So you still have one head + one hook; the hook just contains another product-type word. To avoid that:

- Prefer hook terms that are **not** product-type words (e.g. “steinoptik” only), or  
- Rely on the logic that strips from the hook any token that matches an approved **head** term for the product type (so “duschwanne” can be removed from the hook when it’s a head term).

## Main code references

| What | Where |
|------|--------|
| Render title from template | `pub/services/title_renderer.py` → `render_title()` |
| Resolve head term (one) | `_resolve_head_term()` |
| Resolve hook term (one) | `_resolve_hook_term()` |
| Strip head-like tokens from hook | `_strip_head_tokens()` |
| Resolve axis (variation) attributes | `_resolve_axis_attribute()` |
| Build final string, dedupe | `_clean_title_parts()` |
| Save run + output, enforce uniqueness | `pub/services/title_renderer.py` → `save_generation()` |
| Uniqueness suffix (SKU last 4 / variant id) | `_reserve_unique_title()` |
| Listing “Generate titles” entrypoint | `catalog/services/channel_listings.py` → `generate_titles_for_listing()` |

## Checklist for clean titles

1. **Saved terms**  
   In **Keywords → Saved terms**: one (or more) head terms for the product type, one (or more) hook terms for the product. The script will pick one head and one hook.

2. **Template**  
   In **Listings → [listing] → Titles → Build template**: order = **Head term** → (optional literal) → **Hook term** → **Axis attribute** (for each variation axis: size, colour, finish, etc.). So each variant gets a different title and you avoid “LATE”/“OOTH” suffixes.

3. **Hook wording**  
   Prefer hook terms that don’t repeat the product type (e.g. “steinoptik” instead of “duschwanne steinoptik” if “duschwanne” is already a head term), or rely on the strip logic above.
