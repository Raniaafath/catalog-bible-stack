# Attribute Scoping: Product-Level vs Variant-Level

## Overview

Attribute values in `catalog_productattributevalue` can be stored at either:
- **Product-level**: Shared across all variants of a product family
- **Variant-level**: Specific to each individual variant/SKU

This document explains how to determine the correct scope and how to migrate attributes.

---

## How to Check Attribute Scope

### Database Query

```sql
-- Check all attribute values and their scope
SELECT 
    CASE 
        WHEN product_id IS NOT NULL AND variant_id IS NULL THEN 'Product-level (✅ Valid)'
        WHEN variant_id IS NOT NULL AND product_id IS NULL THEN 'Variant-level (✅ Valid)'
        WHEN product_id IS NOT NULL AND variant_id IS NOT NULL THEN '❌ INVALID: Both set'
        WHEN product_id IS NULL AND variant_id IS NULL THEN '❌ INVALID: Both null'
    END as status,
    COUNT(*) as count
FROM catalog_productattributevalue
GROUP BY status;
```

### Find Invalid Rows

```sql
-- Find rows with both set or both null (inconsistent data)
SELECT 
    id,
    product_id,
    variant_id,
    attribute_id,
    CASE 
        WHEN product_id IS NOT NULL AND variant_id IS NOT NULL THEN '❌ INVALID: Both set'
        WHEN product_id IS NULL AND variant_id IS NULL THEN '❌ INVALID: Both null'
    END as issue
FROM catalog_productattributevalue
WHERE (product_id IS NOT NULL AND variant_id IS NOT NULL)
   OR (product_id IS NULL AND variant_id IS NULL);
```

---

## Rules for Attribute Scoping

### Product-Level Attributes (Shared)

These attributes are **shared across all variants** of a product family:

- **Brand** - Same for all variants
- **Model** - Same for all variants  
- **Series** - Same product line
- **Product Category** - Shared classification
- **Material Family** - Base material type
- **Installation Type** - How it's installed (shared)
- **Product Specifications** - Shared specs
- **General Features** - Features that apply to all variants

**Example**: A "Mountain Bike Pro" family might have:
- Brand: "Trek" (product-level)
- Model: "Mountain Bike Pro" (product-level)
- Material: "Aluminum" (product-level)

### Variant-Level Attributes (Specific)

These attributes **differ between variants**:

- **Color** (`main_color`) - Red vs Blue
- **Size** - Small, Medium, Large
- **Dimensions** - `length_cm`, `width_cm`, `height_cm` (if they vary)
- **Weight** - If different per variant
- **Pack Count** - 1-pack vs 4-pack
- **Format** - Different packaging formats
- **Any attribute that varies per SKU**

**Example**: A "Mountain Bike Pro" family might have variants:
- Variant 1: Color="Red", Size="Small"
- Variant 2: Color="Red", Size="Large"
- Variant 3: Color="Blue", Size="Small"

All have the same Brand/Model (product-level), but different Color/Size (variant-level).

---

## Identifying Attributes to Migrate

### Method 1: Check ProductTypeAttribute.variant_level

The `ProductTypeAttribute` model has a `variant_level` field that indicates whether an attribute should be variant-level:

```sql
-- Check which attributes are marked as variant_level
SELECT 
    a.code as attribute_code,
    pta.variant_level,
    pta.product_type_id
FROM catalog_producttypeattribute pta
JOIN catalog_attribute a ON a.id = pta.attribute_id
WHERE pta.variant_level = true;
```

### Method 2: Common Variant-Level Attribute Names

Attributes with these codes/patterns are typically variant-level:

- `color`, `main_color`, `couleur`
- `size`, `taille`
- `length_cm`, `width_cm`, `height_cm` (if they vary per variant)
- `weight_kg` (if it varies)
- `format`, `pack_count`, `quantity`

### Method 3: Check If Values Differ Per Variant

If a product has multiple variants and the attribute value differs between them, it should be variant-level:

```sql
-- Find attributes that differ between variants of the same product
SELECT 
    p.code as product_code,
    a.code as attribute_code,
    COUNT(DISTINCT pav.value_text) as distinct_values,
    COUNT(DISTINCT v.id) as variant_count
FROM catalog_productattributevalue pav
JOIN catalog_product p ON p.id = pav.product_id
JOIN catalog_attribute a ON a.id = pav.attribute_id
JOIN catalog_variant v ON v.product_id = p.id
WHERE pav.product_id IS NOT NULL
  AND pav.variant_id IS NULL
GROUP BY p.code, a.code
HAVING COUNT(DISTINCT pav.value_text) > 1
   AND COUNT(DISTINCT v.id) > 1;
```

**Note**: If values differ per variant but are stored at product-level, you have a data issue that needs fixing.

---

## Migration Process

### Using the Migration Script

We have a script to help migrate attributes from product-level to variant-level:

```bash
# Dry run (see what would be done)
python manage.py shell < scripts/migrate_attributes_to_variant_level.py

# Or in Django shell
python manage.py shell
>>> exec(open('scripts/migrate_attributes_to_variant_level.py').read())
```

The script will:
1. Identify attributes that should be variant-level
2. Show what would be migrated (dry run)
3. Migrate attribute values from products to variants
4. Mark attributes as `variant_level` in `ProductTypeAttribute`

### Manual Migration

If you need to manually migrate a specific attribute:

```python
from catalog.models import ProductAttributeValue, Variant

# Get all product-level values for an attribute
product_values = ProductAttributeValue.objects.filter(
    attribute__code='main_color',
    product_id__isnull=False,
    variant_id__isnull=True
)

# For each product, move to its variants
for pav in product_values:
    product = pav.product
    variants = Variant.objects.filter(product=product)
    
    for variant in variants:
        # Create variant-level value
        ProductAttributeValue.objects.create(
            variant=variant,
            product=None,
            attribute=pav.attribute,
            attribute_value=pav.attribute_value,
            value_text=pav.value_text,
            value_number=pav.value_number,
            # ... copy other fields
        )
    
    # Delete product-level value
    pav.delete()
```

---

## Current State Check

### Summary Query

```sql
SELECT 
    'Total attribute values' as metric,
    COUNT(*)::text as value
FROM catalog_productattributevalue
UNION ALL
SELECT 
    'Product-level (valid)' as metric,
    COUNT(*)::text as value
FROM catalog_productattributevalue
WHERE product_id IS NOT NULL AND variant_id IS NULL
UNION ALL
SELECT 
    'Variant-level (valid)' as metric,
    COUNT(*)::text as value
FROM catalog_productattributevalue
WHERE variant_id IS NOT NULL AND product_id IS NULL
UNION ALL
SELECT 
    '❌ Invalid (both set)' as metric,
    COUNT(*)::text as value
FROM catalog_productattributevalue
WHERE product_id IS NOT NULL AND variant_id IS NOT NULL
UNION ALL
SELECT 
    '❌ Invalid (both null)' as metric,
    COUNT(*)::text as value
FROM catalog_productattributevalue
WHERE product_id IS NULL AND variant_id IS NULL;
```

---

## Common Issues

### Issue 1: All Attributes at Product-Level

**Symptom**: All attributes are stored at product-level, even variant-specific ones like color.

**Cause**: Import process didn't properly scope attributes.

**Fix**: Use migration script to move variant-specific attributes.

### Issue 2: Attribute Values Differ Per Variant But Stored at Product-Level

**Symptom**: Multiple variants of same product have different values for a product-level attribute.

**Cause**: Data was imported incorrectly.

**Fix**: Move the attribute to variant-level and ensure each variant has its own value.

### Issue 3: Both product_id and variant_id Set

**Symptom**: `ProductAttributeValue` rows have both `product_id` and `variant_id` set.

**Cause**: Data corruption or migration error.

**Fix**: These rows violate the constraint. Clean them up:
```sql
-- Find and delete invalid rows
DELETE FROM catalog_productattributevalue
WHERE product_id IS NOT NULL AND variant_id IS NOT NULL;
```

---

## Best Practices

1. **Set variant_level when creating ProductTypeAttribute**
   ```python
   ProductTypeAttribute.objects.create(
       product_type=product_type,
       attribute=color_attribute,
       variant_level=True,  # ✅ Mark as variant-level
   )
   ```

2. **Check ProductTypeAttribute.variant_level when importing**
   - If `variant_level=True`, store at variant level
   - If `variant_level=False`, store at product level

3. **Validate scope after import**
   - Run consistency checks
   - Ensure variant-level attributes are on variants
   - Ensure product-level attributes are on products

4. **Review attribute scoping periodically**
   - As products evolve, some attributes may need rescoping
   - Use migration script to fix scope issues

---

## Summary

- **Product-level** = Shared across all variants (brand, model, category)
- **Variant-level** = Differs per variant (color, size, dimensions if they vary)
- **Check scope** using SQL queries above
- **Migrate** using the migration script
- **Validate** using consistency checks

The key question: **"Does this attribute value differ between variants of the same product?"**
- Yes → Variant-level
- No → Product-level
