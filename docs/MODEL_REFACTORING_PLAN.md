# Model Refactoring Plan: Product vs Variant

## Current Problem

**Product** (parent/group) currently has fields that belong to **Variant** (individual SKU):
- `source_title` → Should be on Variant
- `source_description` → Should be on Variant  
- `source_sku` → Should be on Variant
- `source_supplier` → Should be on Variant
- `source_locale` → Should be on Variant

## Correct Model Structure

### Product (ProductFamily/ProductGroup)
**Purpose**: Container/group for variants
**Fields**:
- `code` (unique identifier for the group)
- `product_type_id` (FK)
- `default_label` (general title for the group)
- `brand`, `model`, `series` (shared across variants)
- `status` (draft/active/discontinued)
- Variation axes (stored in `ProductVariantAxis`)

**Does NOT have**:
- ❌ `source_title`, `source_description` (variant-specific)
- ❌ `source_sku` (variant-specific)
- ❌ `sku` (variant-specific)

### Variant (Individual SKU)
**Purpose**: The actual sellable item
**Fields**:
- `product_id` (FK to Product/group)
- `sku` (unique identifier)
- `barcode`, `mpn`
- `source_title` (from import/supplier)
- `source_description` (from import/supplier)
- `source_sku` (from import/supplier)
- `source_supplier` (from import/supplier)
- `source_locale` (from import/supplier)
- `axis_signature` (for quick lookup)

## Migration Plan

1. **Add fields to Variant model**
2. **Create migration to move data** (if any exists)
3. **Remove fields from Product model**
4. **Update import logic** to put source fields on Variant
5. **Update serializers** to reflect new structure
6. **Update admin** to show source fields on Variant

## Optional: Rename Product → ProductFamily?

**Current name**: `Product`
**Proposed name**: `ProductFamily` or `ProductGroup`

**Pros**:
- More accurate (it's a family/group, not a single product)
- Clearer intent

**Cons**:
- Breaking change (requires migration, code updates everywhere)
- More verbose

**Recommendation**: Keep `Product` name but document it clearly as "Product Family/Group"
