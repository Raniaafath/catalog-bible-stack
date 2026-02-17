# Attribute Migration Guide: Product-Level → Variant-Level

## Overview

This guide explains how to safely migrate attribute values from product-level to variant-level using the deterministic migration script.

---

## Prerequisites

### Step 1: Mark Variant-Level Attributes

Before running the migration, mark which attributes should be variant-level for each product type.

**Method A: Admin UI (Recommended)**

1. Go to Django Admin → Product Types
2. Select a Product Type
3. Edit the Attributes section
4. For each attribute that should be variant-level, set `variant_level=True`
5. Save

**Method B: Django Shell**

```python
from catalog.models import ProductTypeAttribute, ProductType, Attribute

# Mark an attribute as variant-level for a product type
product_type = ProductType.objects.get(code='your-product-type')
attribute = Attribute.objects.get(code='main_color')

ProductTypeAttribute.objects.update_or_create(
    product_type=product_type,
    attribute=attribute,
    defaults={'variant_level': True}
)
```

**Attributes typically marked as variant-level:**
- `main_color`, `color`, `couleur` (colors)
- `length_cm`, `width_cm`, `height_cm` (dimensions - if they vary per variant)
- `weight_kg` (if it varies)
- `size`, `format`, `pack_count` (variant-specific options)

**Attributes typically kept at product-level:**
- `brand`, `model`, `series` (shared across variants)
- `product_category`, `material_family` (shared classifications)
- `installation_type` (shared specs)

---

## Migration Process

### Step 2: Run Dry Run

First, see what would be migrated without making any changes:

```bash
python manage.py shell < scripts/migrate_attributes_to_variant_level.py
```

The script will:
1. Find all `ProductTypeAttribute` records where `variant_level=True`
2. Find all product-level attribute values for those attributes
3. Analyze what would be migrated
4. Show detailed report including:
   - Total values to migrate
   - Products affected
   - Variants that will get new values
   - Conflicts (variants that already have the attribute)

**Example Output:**
```
MIGRATION ANALYSIS REPORT
================================================================================

✅ Found 5 variant-level attribute configurations

Variant-level attributes by product type:
--------------------------------------------------------------------------------
  receveur-de-doucher:
    - height_cm
    - length_cm
    - main_color
    - width_cm

📊 Migration Statistics:
--------------------------------------------------------------------------------
  Total product-level values to migrate: 37
  Products affected: 3
  Variants that will get new attribute values: 12
  Conflicts (variant already has value): 0

⚠️  DRY RUN MODE - No actual changes will be made
```

### Step 3: Review Report

Carefully review the report:
- ✅ Check that the attributes listed are correct
- ✅ Verify the products affected are correct
- ✅ Note any conflicts (variants that already have values)
- ⚠️  If conflicts exist, decide if you want to skip or overwrite

### Step 4: Run Actual Migration

Once you're satisfied with the report, run the actual migration:

**Option A: Edit the script**

Open `scripts/migrate_attributes_to_variant_level.py` and uncomment the last line:

```python
# Uncomment to automatically perform migration:
migrate_attributes_to_variant_level(variant_level_attrs, dry_run=False)
verify_migration(attribute_codes=['main_color', 'length_cm', 'width_cm', 'height_cm'])
```

Then run:
```bash
python manage.py shell < scripts/migrate_attributes_to_variant_level.py
```

**Option B: Django Shell**

```python
python manage.py shell

>>> exec(open('scripts/migrate_attributes_to_variant_level.py').read())
>>> migrate_attributes_to_variant_level(variant_level_attrs, dry_run=False)
>>> verify_migration(attribute_codes=['main_color', 'length_cm', 'width_cm', 'height_cm'])
```

---

## How the Script Works

### Deterministic Logic

The script uses **ProductTypeAttribute.variant_level** as the authoritative source:

1. **Build target set**: `{(product_type_id, attribute_id) where ProductTypeAttribute.variant_level=True}`

2. **For each product**:
   - Determine its `product_type_id`
   - Check if it has product-level attribute values
   - Only migrate attributes in the target set for that product type

3. **For each attribute value to migrate**:
   - Find all variants of the product
   - For each variant:
     - Check if variant already has this attribute (skip if exists)
     - Copy all fields exactly (attribute_value, value_text, value_number, etc.)
     - Set `product_id=NULL`, `variant_id=variant.id`
   - Delete the product-level attribute value

### Safety Features

- ✅ **Deterministic**: Only migrates attributes marked as `variant_level=True` in ProductTypeAttribute
- ✅ **Dry run**: Shows exactly what would be done before making changes
- ✅ **No overwrites**: Skips variants that already have the attribute
- ✅ **Transaction-wrapped**: All-or-nothing migration
- ✅ **Complete field copying**: Copies all value fields (text, number, bool, json, enum FK, unit, is_axis)
- ✅ **Detailed reporting**: Shows counts, conflicts, and breakdown by product type

---

## Verification

### Step 5: Verify Migration

After migration, verify the results:

**SQL Verification:**

```sql
-- Should be >0 after migration
SELECT COUNT(*) as variant_level_values
FROM catalog_productattributevalue 
WHERE variant_id IS NOT NULL;

-- For migrated attributes: should be 0 at product-level
SELECT pav.id, pav.product_id, pav.variant_id, a.code
FROM catalog_productattributevalue pav
JOIN catalog_attribute a ON a.id = pav.attribute_id
WHERE pav.product_id IS NOT NULL
  AND a.code IN ('main_color', 'length_cm', 'width_cm', 'height_cm')
LIMIT 50;
```

**Using the script:**

The script includes a `verify_migration()` function that checks:
- Total variant-level values
- Whether migrated attributes are still at product-level

---

## Database Constraints

### XOR Constraint (Already Exists)

The database already has a constraint that enforces exactly one of `product_id` or `variant_id` must be set:

**Constraint name**: `chk_attribute_value_scope`

**Definition**: 
```sql
CHECK (
    ((product_id IS NOT NULL) AND (variant_id IS NULL)) 
    OR 
    ((product_id IS NULL) AND (variant_id IS NOT NULL))
)
```

This ensures data consistency - you can never have both or neither set.

---

## Common Scenarios

### Scenario 1: Product with Multiple Variants

**Before:**
- Product "BIKE-001" has `main_color="Red"` at product-level
- Variants: "BIKE-001-RED-S", "BIKE-001-RED-L"

**After:**
- Variant "BIKE-001-RED-S" has `main_color="Red"` at variant-level
- Variant "BIKE-001-RED-L" has `main_color="Red"` at variant-level
- Product "BIKE-001" no longer has `main_color` at product-level

### Scenario 2: Product with One Variant

**Before:**
- Product "PROD-001" has `main_color="Blue"` at product-level
- Variant: "PROD-001-BLUE"

**After:**
- Variant "PROD-001-BLUE" has `main_color="Blue"` at variant-level
- Product "PROD-001" no longer has `main_color` at product-level

**Note**: This is the current situation - most products have 1 variant. The script handles this efficiently.

### Scenario 3: Variant Already Has Attribute (Conflict)

**Before:**
- Product "PROD-002" has `main_color="Green"` at product-level
- Variant "PROD-002-GREEN" already has `main_color="Green"` at variant-level

**After:**
- Variant keeps its existing value (no duplicate created)
- Product-level value is deleted
- Script reports the conflict

---

## Import Process After Migration

### Important: Update Import Logic

After migrating attributes to variant-level, ensure your import process respects `ProductTypeAttribute.variant_level`:

**Import logic should check:**

```python
# When importing attributes
product_type_attribute = ProductTypeAttribute.objects.get(
    product_type=product.product_type,
    attribute=attribute
)

if product_type_attribute.variant_level:
    # Store at variant level
    ProductAttributeValue.objects.create(
        variant=variant,
        product=None,
        attribute=attribute,
        # ... value fields
    )
else:
    # Store at product level
    ProductAttributeValue.objects.create(
        product=product,
        variant=None,
        attribute=attribute,
        # ... value fields
    )
```

This prevents future imports from undoing the migration.

---

## Troubleshooting

### Issue: "No variant-level attributes found"

**Solution**: Mark attributes as `variant_level=True` in ProductTypeAttribute first.

### Issue: "Product has no variants"

**Solution**: The script will skip these. Make sure products have variants before migrating.

### Issue: "Conflict: variant already has value"

**Solution**: The script skips these. If you want to overwrite, you'll need to modify the script to delete existing variant values first.

### Issue: "Migration seems incomplete"

**Solution**: 
1. Run verification SQL queries
2. Check that ProductTypeAttribute.variant_level=True for all attributes you want migrated
3. Verify products have variants

---

## Summary

1. **Mark variant-level attributes** in ProductTypeAttribute
2. **Run dry run** to see what would be migrated
3. **Review report** carefully
4. **Run actual migration** with dry_run=False
5. **Verify results** using SQL or script verification
6. **Update import logic** to respect variant_level flag

The migration is deterministic, safe, and reversible (if you keep backups). All changes are wrapped in a transaction, so it's all-or-nothing.
