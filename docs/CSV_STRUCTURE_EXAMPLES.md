# CSV Structure Examples for Parent-Variant Import

## Two Ways to Structure Your CSV

### Option 1: All Rows Are Variants (Simpler - Recommended)

**Every row = one variant**. Group them using the same `parent_id`.

```csv
parent_id,sku,brand,title,color,size,price,barcode
BIKE-001,BIKE-001-RED-M,Trek,Mountain Bike Pro,Red,Medium,599.99,123001
BIKE-001,BIKE-001-RED-L,Trek,Mountain Bike Pro,Red,Large,649.99,123002
BIKE-001,BIKE-001-BLUE-M,Trek,Mountain Bike Pro,Blue,Medium,599.99,123003
BIKE-001,BIKE-001-BLUE-L,Trek,Mountain Bike Pro,Blue,Large,649.99,123004
PHONE-002,PHONE-002-BLK-64,Samsung,Galaxy S24,Black,64GB,799.99,456001
PHONE-002,PHONE-002-BLK-128,Samsung,Galaxy S24,Black,128GB,899.99,456002
PHONE-002,PHONE-002-WHT-64,Samsung,Galaxy S24,White,64GB,799.99,456003
PHONE-002,PHONE-002-WHT-128,Samsung,Galaxy S24,White,128GB,899.99,456004
```

**What gets created:**

```
Product: BIKE-001
  ├─ brand: Trek
  ├─ title: Mountain Bike Pro (from first row)
  ├─ Variation Axes: color (position 0), size (position 1)
  └─ Variants:
      ├─ BIKE-001-RED-M   (axis_signature: "red:medium")
      ├─ BIKE-001-RED-L   (axis_signature: "red:large")
      ├─ BIKE-001-BLUE-M  (axis_signature: "blue:medium")
      └─ BIKE-001-BLUE-L  (axis_signature: "blue:large")

Product: PHONE-002
  ├─ brand: Samsung
  ├─ title: Galaxy S24
  ├─ Variation Axes: color (position 0), size (position 1)
  └─ Variants:
      ├─ PHONE-002-BLK-64   (axis_signature: "black:64gb")
      ├─ PHONE-002-BLK-128  (axis_signature: "black:128gb")
      ├─ PHONE-002-WHT-64   (axis_signature: "white:64gb")
      └─ PHONE-002-WHT-128  (axis_signature: "white:128gb")
```

**Pros:**
- ✅ Simple and clear
- ✅ Easy to export from most systems
- ✅ Repeating data is OK (brand, title)
- ✅ All information visible on each row

**Cons:**
- ❌ Some data duplication (brand/title repeated)

---

### Option 2: Parent Row + Variant Rows (More Structured)

**First row = parent product** (shared data)  
**Following rows = variants** (unique data)

```csv
parent_id,sku,brand,title,color,size,price,barcode
BIKE-001,BIKE-001,Trek,Mountain Bike Pro,,,0,
BIKE-001,BIKE-001-RED-M,,,Red,Medium,599.99,123001
BIKE-001,BIKE-001-RED-L,,,Red,Large,649.99,123002
BIKE-001,BIKE-001-BLUE-M,,,Blue,Medium,599.99,123003
BIKE-001,BIKE-001-BLUE-L,,,Blue,Large,649.99,123004
PHONE-002,PHONE-002,Samsung,Galaxy S24,,,0,
PHONE-002,PHONE-002-BLK-64,,,Black,64GB,799.99,456001
PHONE-002,PHONE-002-BLK-128,,,Black,128GB,899.99,456002
PHONE-002,PHONE-002-WHT-64,,,White,64GB,799.99,456003
PHONE-002,PHONE-002-WHT-128,,,White,128GB,899.99,456004
```

**Pattern:**
- **Parent row**: Has product data (brand, title), empty variant data (color, size, price)
- **Variant rows**: Have variant data (color, size, price), empty product data

**Creates the exact same structure as Option 1!**

**Pros:**
- ✅ No data duplication
- ✅ Clear separation of product vs variant data
- ✅ Easier to update product data (one row)

**Cons:**
- ❌ Slightly more complex structure
- ❌ Parent row must come first in each group
- ❌ Harder to see full info on each variant row

---

## Real-World Example: Clothing Store

### Option 1 Structure (All Rows = Variants)

```csv
parent_id,sku,brand,model,title,category,color,size,material,price,stock
SHIRT-101,SHIRT-101-BLK-S,Nike,Dri-FIT,Running Shirt,Apparel,Black,Small,Polyester,29.99,50
SHIRT-101,SHIRT-101-BLK-M,Nike,Dri-FIT,Running Shirt,Apparel,Black,Medium,Polyester,29.99,75
SHIRT-101,SHIRT-101-BLK-L,Nike,Dri-FIT,Running Shirt,Apparel,Black,Large,Polyester,29.99,60
SHIRT-101,SHIRT-101-WHT-S,Nike,Dri-FIT,Running Shirt,Apparel,White,Small,Polyester,29.99,45
SHIRT-101,SHIRT-101-WHT-M,Nike,Dri-FIT,Running Shirt,Apparel,White,Medium,Polyester,29.99,80
SHIRT-101,SHIRT-101-WHT-L,Nike,Dri-FIT,Running Shirt,Apparel,White,Large,Polyester,29.99,55
PANTS-102,PANTS-102-NVY-30,Adidas,Tiro,Training Pants,Apparel,Navy,30,Cotton,49.99,30
PANTS-102,PANTS-102-NVY-32,Adidas,Tiro,Training Pants,Apparel,Navy,32,Cotton,49.99,40
PANTS-102,PANTS-102-BLK-30,Adidas,Tiro,Training Pants,Apparel,Black,30,Cotton,49.99,35
PANTS-102,PANTS-102-BLK-32,Adidas,Tiro,Training Pants,Apparel,Black,32,Cotton,49.99,45
```

**Result:**
- 2 Products (SHIRT-101, PANTS-102)
- 10 Variants total (6 shirts + 4 pants)
- Detected axes: `color`, `size` for both
- Product-level: brand, model, title, category, material
- Variant-level: color, size, price, stock

### Option 2 Structure (Parent + Variants)

```csv
parent_id,sku,brand,model,title,category,color,size,material,price,stock
SHIRT-101,SHIRT-101,Nike,Dri-FIT,Running Shirt,Apparel,,,,0,0
SHIRT-101,SHIRT-101-BLK-S,,,,,Black,Small,,29.99,50
SHIRT-101,SHIRT-101-BLK-M,,,,,Black,Medium,,29.99,75
SHIRT-101,SHIRT-101-BLK-L,,,,,Black,Large,,29.99,60
SHIRT-101,SHIRT-101-WHT-S,,,,,White,Small,,29.99,45
SHIRT-101,SHIRT-101-WHT-M,,,,,White,Medium,,29.99,80
SHIRT-101,SHIRT-101-WHT-L,,,,,White,Large,,29.99,55
PANTS-102,PANTS-102,Adidas,Tiro,Training Pants,Apparel,,,,0,0
PANTS-102,PANTS-102-NVY-30,,,,,Navy,30,,49.99,30
PANTS-102,PANTS-102-NVY-32,,,,,Navy,32,,49.99,40
PANTS-102,PANTS-102-BLK-30,,,,,Black,30,,49.99,35
PANTS-102,PANTS-102-BLK-32,,,,,Black,32,,49.99,45
```

**Same result as Option 1!**

---

## Which Structure to Use?

### Use Option 1 (All Rows = Variants) if:
- ✅ You're exporting from Shopify, WooCommerce, or similar
- ✅ Your source system doesn't separate parent/variant rows
- ✅ You want simpler, more readable files
- ✅ Data duplication is not a concern

### Use Option 2 (Parent + Variants) if:
- ✅ You're creating files manually
- ✅ You want to minimize data duplication
- ✅ Product data is extensive (many shared fields)
- ✅ You update product data frequently (one row to change)

---

## What the System Detects Automatically

Regardless of which structure you use:

### 1. Parent Grouping
- Uses `parent_id` column (or similar: `product_id`, `group_id`, `handle`)
- All rows with same ID = one product

### 2. Variation Axes
- Finds columns with different values across variants
- Prioritizes: color, size, capacity, material, style, finish
- Limits to 2-20 unique values per axis
- Stores up to 5 axes per product

### 3. Product vs Variant Level
- **Product-level** (same for all variants): brand, model, category, material
- **Variant-level** (different per variant): color, size, price, stock, barcode

### 4. Axis Signature
- Each variant gets signature from axis values
- Examples:
  - `red:medium` for Red + Medium
  - `black:64gb` for Black + 64GB
  - `navy:30:regular` for Navy + Size 30 + Regular fit

---

## Common Column Names Detected

The system recognizes these column names automatically:

### Parent/Product Key
- `parent_id`, `product_id`, `group_id`, `handle`, `parent_sku`, `model_id`

### Variant/SKU Key
- `sku`, `variant_sku`, `ean`, `barcode`, `gtin`, `id_variant`, `variant_id`

### Standard Fields
- **Category**: `category`, `product_type`, `type`
- **Brand**: `brand`, `manufacturer`, `vendor`
- **Title**: `title`, `name`, `product_name`
- **Description**: `description`, `desc`, `body_html`

### Common Variation Axes
- **Color**: `color`, `colour`, `couleur`
- **Size**: `size`, `taille`
- **Capacity**: `capacity`, `capacite`, `storage`
- **Material**: `material`, `materiau`
- **Style**: `style`, `finish`, `finition`

---

## What Gets Stored in Database

### Products Table
```python
Product(
    code='shirt-101',
    brand='Nike',
    model='Dri-FIT',
    default_label='Running Shirt',
    product_type=apparel_type
)
```

### ProductVariantAxis Table (The Key!)
```python
ProductVariantAxis(product=shirt_product, attribute=color_attr, position=0)
ProductVariantAxis(product=shirt_product, attribute=size_attr, position=1)
```
**This is what you'll use later for title generation!**

### Variants Table
```python
Variant(
    product=shirt_product,
    sku='SHIRT-101-BLK-S',
    axis_signature='black:small',  # Built from axes
    barcode='...'
)
```

### ProductAttributeValue Table
```python
# Variant-level (color axis)
ProductAttributeValue(
    variant=variant_blk_s,
    attribute=color_attr,
    attribute_value=black_value,
    is_axis=True  # ← Marks it as variation axis!
)

# Variant-level (size axis)
ProductAttributeValue(
    variant=variant_blk_s,
    attribute=size_attr,
    attribute_value=small_value,
    is_axis=True  # ← Marks it as variation axis!
)

# Product-level (material - same for all)
ProductAttributeValue(
    product=shirt_product,
    attribute=material_attr,
    value_text='Polyester',
    is_axis=False
)
```

---

## Title Generation - Done LATER

The import **does NOT generate titles**. It just stores the structure.

**When you need titles later:**

```python
from catalog.services import generate_variant_title
from catalog.models import Variant

# Get a variant
variant = Variant.objects.get(sku='SHIRT-101-BLK-S')

# Generate title using stored axes
title = generate_variant_title(variant)
# Result: "Running Shirt - Black Small"

# Or with custom template
from catalog.services import generate_variant_title_template

generator = generate_variant_title_template(
    variant.product,
    template="{base_title} in {color} ({size})"
)
title = generator(variant)
# Result: "Running Shirt in Black (Small)"
```

---

## Summary

**Import Step (Now):**
- ✅ Upload CSV (either structure)
- ✅ System groups by parent_id
- ✅ Detects variation axes automatically
- ✅ Stores products, variants, axes, signatures
- ❌ Does NOT generate titles

**Title Generation (Later):**
- When displaying products in catalog
- When generating SEO meta tags
- When creating product feeds
- When exporting to other systems

The stored variation axes (`ProductVariantAxis`) tell the system **which attributes to use** and **in what order** when generating titles later!
