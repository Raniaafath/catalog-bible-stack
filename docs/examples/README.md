# Example CSV Files for Product Import

This folder contains example CSV files showing how to structure your product data for import.

## Files

### 1. products_import_example.csv
**Structure**: All rows are variants (Option 1 - Recommended)

This is the **simpler format** where every row represents a variant, and shared data (brand, title) is repeated.

**Use this if:**
- You're exporting from Shopify, WooCommerce, or similar platforms
- You want a simple, easy-to-read structure
- Data repetition is not a concern

**What gets created:**
- 3 Products (BIKE-001, PHONE-002, SHIRT-003)
- 14 Variants total (4 bikes + 4 phones + 6 shirts)
- Detected axes: color, size for each product

### 2. products_import_parent_variant.csv
**Structure**: Parent row + variant rows (Option 2)

This format has a parent row with shared data, followed by variant-specific rows.

**Use this if:**
- You're creating files manually
- You want to minimize data duplication
- You have extensive product data that's the same for all variants

**What gets created:**
- Same result as Option 1!
- 3 Products, 14 Variants, with same axes detected

## How to Use These Examples

### 1. Download and Test
```bash
# Copy one of these files to test the import
cp docs/examples/products_import_example.csv /tmp/test_import.csv

# Then import it using the admin interface or API
```

### 2. Use as Template
Open either file in Excel/Google Sheets and:
- Replace the data with your products
- Keep the column structure
- Ensure `parent_id` groups related variants
- Each variant needs a unique `sku`

### 3. Understand the Structure

Both files contain the same products:

**BIKE-001** (Mountain Bike Pro by Trek)
- 4 variants: Red/Blue × Medium/Large
- Material: Aluminum (same for all)
- Axes: color, size

**PHONE-002** (Galaxy S24 by Samsung)
- 4 variants: Black/White × 64GB/128GB
- Material: Glass (same for all)
- Axes: color, size (capacity)

**SHIRT-003** (Running Shirt by Nike)
- 6 variants: Red/Blue × Small/Medium/Large
- Material: Polyester (same for all)
- Axes: color, size

## What Happens After Import

After importing either file:

### Database Structure
```
Product: bike-001
  ├─ brand: Trek
  ├─ title: Mountain Bike Pro
  ├─ ProductVariantAxis[0]: color
  ├─ ProductVariantAxis[1]: size
  └─ Variants:
      ├─ BIKE-001-RED-M (axis_signature: "red:medium")
      ├─ BIKE-001-RED-L (axis_signature: "red:large")
      ├─ BIKE-001-BLUE-M (axis_signature: "blue:medium")
      └─ BIKE-001-BLUE-L (axis_signature: "blue:large")

Product: phone-002
  ├─ brand: Samsung
  ├─ title: Galaxy S24
  ├─ ProductVariantAxis[0]: color
  ├─ ProductVariantAxis[1]: size
  └─ Variants:
      ├─ PHONE-002-BLK-64 (axis_signature: "black:64gb")
      ├─ PHONE-002-BLK-128 (axis_signature: "black:128gb")
      ├─ PHONE-002-WHT-64 (axis_signature: "white:64gb")
      └─ PHONE-002-WHT-128 (axis_signature: "white:128gb")

Product: shirt-003
  ├─ brand: Nike
  ├─ title: Running Shirt
  ├─ ProductVariantAxis[0]: color
  ├─ ProductVariantAxis[1]: size
  └─ Variants: (6 total)
      └─ ... (Red/Blue × S/M/L combinations)
```

### Attributes Stored

**Product-level** (same for all variants):
- brand, title, category, material

**Variant-level** (different per variant):
- color, size, price, stock, barcode

**Variation Axes** (marked with `is_axis=True`):
- color, size

## Verify Import Results

After import, check the results:

```python
from catalog.models import Product, ProductVariantAxis

# Check products created
products = Product.objects.all()
print(f"Products: {products.count()}")  # Should be 3

# Check variants
for product in products:
    print(f"\n{product.code}:")
    print(f"  Variants: {product.variants.count()}")
    
    # Check variation axes
    axes = product.variant_axes.order_by('position')
    print(f"  Axes: {', '.join(a.attribute.code for a in axes)}")

# Expected output:
# bike-001:
#   Variants: 4
#   Axes: color, size
# phone-002:
#   Variants: 4
#   Axes: color, size
# shirt-003:
#   Variants: 6
#   Axes: color, size
```

## Need Help?

- See `../QUICK_START.md` for usage instructions
- See `../CSV_STRUCTURE_EXAMPLES.md` for detailed format explanation
- See `../PARENT_VARIANT_IMPORT.md` for complete documentation
