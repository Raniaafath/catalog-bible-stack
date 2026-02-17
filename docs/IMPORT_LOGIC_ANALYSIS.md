# Import Logic Analysis: Product and Variant Creation

## Overview

This document analyzes the import process to verify that it correctly handles the Product → Variant relationship and attribute scoping.

---

## ✅ Correct: Relationship is Product → Variant (Not the Reverse)

The import logic **correctly** creates:
- **Product** (parent) first
- **Variant** (child) with `product_id` FK pointing to Product

It does **NOT** upsert products inside variants. The relationship is correct: `Variant.product_id` → `Product.id`.

---

## Import Process Flow

### Step 1: Check if Variant Exists (Lookup)

```python
# Line 359-367: Check for existing variant
existing_variant = None
if variant_sku:
    existing_variant = Variant.objects.filter(sku=variant_sku).first()
if not existing_variant and variant_barcode:
    existing_variant = Variant.objects.filter(barcode=variant_barcode).first()

variant_is_new = existing_variant is None
```

**Purpose**: Check if this variant already exists (by SKU or barcode).

---

### Step 2: Determine/Create Product

**If variant is NEW:**

```python
# Line 372-440: Create/update product
if variant_is_new:
    # Determine product code based on mode
    if use_grouping_mode and product_key_col:
        # Mode B: Group by PRODUCT_KEY
        product_code = slugify(parent_key)
    else:
        # Mode A: Standalone (one product per variant)
        product_code = slugify(variant_sku)
    
    # Create or update product
    target_product, product_created = Product.objects.update_or_create(
        code=product_code,
        defaults=product_data
    )
```

**If variant EXISTS:**

```python
# Line 441-444: Safety rule - don't change product_id
else:
    # Existing variant: SAFETY RULE - don't change product_id (preserve manual grouping)
    target_product = existing_variant.product
    # Don't update product fields (may have been merged/edited manually)
```

**Key point**: For existing variants, it **preserves** the existing `product_id` - it doesn't change it. This protects manual grouping.

---

### Step 3: Create/Update Variant

**If variant is NEW:**

```python
# Line 484-489: Create new variant
if variant_is_new:
    variant_defaults = {
        'product': target_product,  # ✅ FK to Product
    }
    variant = Variant.objects.create(**variant_defaults)
```

**If variant EXISTS:**

```python
# Line 491-508: Update existing variant (but preserve product_id)
else:
    # Update existing variant (but preserve product_id if it was manually set)
    # Only update safe fields: barcode, mpn (not product_id)
    update_fields = []
    if variant_barcode:
        existing_variant.barcode = variant_barcode
        update_fields.append('barcode')
    # ... only updates barcode/mpn, NOT product_id
    existing_variant.save(update_fields=update_fields)
```

**Key point**: For existing variants, it **only updates** barcode/mpn, **NOT** `product_id`. This preserves manual grouping.

---

### Step 4: Create Attribute Values

**Product-level attributes** (Line 510-572):

```python
# Only for new products
if variant_is_new:
    for col_name, rule in column_rules.items():
        if rule.variant_level or rule.is_variation_axis:
            continue  # Skip variant-level attributes
        
        # Create ProductAttributeValue
        ProductAttributeValue.objects.update_or_create(
            product=target_product,  # ✅ Product-level
            variant=None,            # ✅ NULL for product-level
            attribute=attribute,
            defaults=pav_data
        )
```

**Variant-level attributes** (Line 574-644):

```python
# For all variants (new or existing)
for col_name, rule in column_rules.items():
    if not (rule.variant_level or rule.is_variation_axis):
        continue  # Skip product-level attributes
    
    # Create ProductAttributeValue
    ProductAttributeValue.objects.update_or_create(
        variant=variant,           # ✅ Variant-level
        product=None,              # ✅ NULL for variant-level
        attribute=attribute,
        defaults=pav_data
    )
```

**Key point**: Respects `rule.variant_level` flag to determine product vs variant scope.

---

## ✅ Verification: Relationship is Correct

The code correctly creates:
- `Variant.objects.create(product=target_product)` ✅
- `ProductAttributeValue(product=target_product, variant=None)` ✅ (product-level)
- `ProductAttributeValue(variant=variant, product=None)` ✅ (variant-level)

**NOT**:
- ❌ `Product.objects.create(variant=...)` (this doesn't exist)
- ❌ Products don't have variant FK

---

## Potential Issues / Improvements

### Issue 1: Docstring is Misleading

**Line 251**: Says "Upsert Variant first" but actually:
1. Checks variant existence (lookup)
2. Creates/updates Product
3. Creates/updates Variant

**Fix**: Docstring should say "Check variant existence first, then create/update Product, then create/update Variant with product_id FK".

### Issue 2: Product-level Attributes Only Created for New Products

**Line 511**: `if variant_is_new:` - Product-level attributes are only created if the variant is new.

**Implication**: If you re-import and variant already exists, product-level attributes won't be updated.

**Question**: Is this intentional? If a product already exists, should product-level attributes be updated?

### Issue 3: Variant-level Attributes Always Created

**Line 574-644**: Variant-level attributes are created for both new and existing variants.

**Implication**: Re-importing will update variant-level attributes.

**This is probably correct** - variant-level attributes should be updated on re-import.

---

## Summary

### ✅ What's Correct

1. **Relationship**: Variants have `product_id` FK → Products (correct direction)
2. **Attribute scoping**: Respects `variant_level` flag correctly
3. **Safety**: Preserves `product_id` for existing variants (protects manual grouping)
4. **Mode support**: Supports both standalone (1 product = 1 variant) and grouping (PRODUCT_KEY)

### ⚠️ Potential Improvements

1. **Docstring**: Update to reflect actual flow
2. **Product-level attributes**: Consider whether to update on re-import
3. **Verification**: Could add checks to verify variant.product_id is set correctly

### ✅ Overall Assessment

The import logic is **correct**. It does **NOT** upsert products inside variants. The relationship is:
- **Product** (parent) ← **Variant.product_id** (child FK)

This matches the correct data model pattern.

---

## Testing Recommendations

To verify the import logic works correctly:

1. **Test new variant import**:
   - Import a CSV with new variants
   - Verify: Variant has `product_id` set correctly
   - Verify: Product-level attributes on Product
   - Verify: Variant-level attributes on Variant

2. **Test existing variant re-import**:
   - Import same variant again
   - Verify: `product_id` is NOT changed
   - Verify: Variant-level attributes are updated
   - Verify: Product-level attributes behavior (may not update - is this intended?)

3. **Test grouping mode**:
   - Import CSV with PRODUCT_KEY column
   - Verify: Multiple variants share same Product
   - Verify: Attributes scoped correctly

4. **Test variant_level flag**:
   - Import with `variant_level=True` for some attributes
   - Verify: Attributes stored at variant-level (variant_id set, product_id NULL)
   - Verify: Attributes with `variant_level=False` stored at product-level (product_id set, variant_id NULL)

---

## Conclusion

The import logic is **correct** and does **NOT** upsert products inside variants. The relationship is properly implemented as:
- Product (parent) → Variant.product_id (child FK)

The code correctly handles:
- ✅ Product creation/update
- ✅ Variant creation with product_id FK
- ✅ Attribute scoping (product vs variant level)
- ✅ Safety rules (preserves existing product_id)

The only minor issue is the misleading docstring that says "Upsert Variant first" when it actually checks variant existence first, then creates product, then creates variant. But the actual logic is correct.
