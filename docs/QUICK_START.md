# Quick Start: Parent-Variant Import

## What This Does

Import CSV files with parent products and multiple variants, automatically detect variation axes (like color, size), and generate variant titles.

## 1. Run Migration

```bash
python manage.py migrate importer
```

## 2. Test with Sample Data

```bash
python manage.py test_parent_variant_import
```

This will:
- Create a sample import with bikes and phones
- Auto-detect color and size as variation axes
- Create products with variants
- Generate titles like "Mountain Bike Pro - Red Medium"

## 3. Use with Your Data

### CSV Structure - Two Options

#### Option 1: All Rows Are Variants (Recommended - Simpler)

Each row is a variant with `parent_id` to group them:

```csv
parent_id,sku,brand,title,color,size,price
SHIRT-001,SHIRT-001-RED-S,Nike,Running Shirt,Red,Small,29.99
SHIRT-001,SHIRT-001-RED-M,Nike,Running Shirt,Red,Medium,29.99
SHIRT-001,SHIRT-001-BLUE-S,Nike,Running Shirt,Blue,Small,29.99
```

**How it works:**
- All rows with same `parent_id` = 1 product
- Each row = 1 variant
- Shared data (brand, title) can be repeated on each row
- System uses first row for product-level data

#### Option 2: Parent Row + Variant Rows (Explicit Structure)

First row has parent data, subsequent rows have only variant-specific data:

```csv
parent_id,sku,brand,title,color,size,price
SHIRT-001,SHIRT-001,Nike,Running Shirt,,,0
SHIRT-001,SHIRT-001-RED-S,,,Red,Small,29.99
SHIRT-001,SHIRT-001-RED-M,,,Red,Medium,29.99
SHIRT-001,SHIRT-001-BLUE-S,,,Blue,Small,29.99
```

**How it works:**
- First row per `parent_id`: parent product data only
- Following rows: variant-specific data only
- Leave variant columns empty in parent row
- Leave product columns empty in variant rows

**Both structures produce the same result:**
- 1 Product: `SHIRT-001`
- 3 Variants: RED-S, RED-M, BLUE-S
- 2 Variation Axes: color, size

### Import in Python

```python
from importer.models import ProductImport, ImportColumnRule
from importer.services import parse_import, process_import

# 1. Upload
import_obj = ProductImport.objects.create(
    source_file=your_file,
    status='uploaded'
)

# 2. Parse
parse_import(import_obj.id)

# 3. Configure axes (optional)
ImportColumnRule.objects.filter(
    product_import=import_obj,
    column_name='color'
).update(is_variation_axis=True, axis_priority=0)

# 4. Process
process_import(import_obj.id)
```

### What Gets Stored (Import Does NOT Generate Titles)

The import **ONLY stores the structure**:
- ✅ Products (one per `parent_id`)
- ✅ Variants (one per row or variant row)
- ✅ Variation Axes (which attributes differentiate variants)
- ✅ Axis Signatures (e.g., `red:small`)
- ✅ Product and variant attributes

### Generate Titles Later (Separate Step)

**Title generation is a separate step** - run it when you need titles:

```python
# LATER: When you need to generate titles for display/SEO
from catalog.services import generate_variant_title
from catalog.models import Product

product = Product.objects.get(code='shirt-001')
for variant in product.variants.all():
    title = generate_variant_title(variant)
    print(f"{variant.sku}: {title}")
    # Result: "Running Shirt - Red Small"
```

## Files Created

### Code
- `importer/migrations/0015_import_parent_variant_handling.py` - Database migration
- `importer/models.py` - Enhanced models (modified)
- `importer/services.py` - Import processing with parent-child support (modified)
- `catalog/services/variant_titles.py` - Title generation service
- `catalog/management/commands/test_parent_variant_import.py` - Test command

### Documentation
- `docs/LISTING_GROUP_WORKFLOW.md` - Title generation after import
- `docs/PARENT_VARIANT_IMPORT.md` - Complete user guide
- `docs/PARENT_VARIANT_EXAMPLE.py` - Working code examples
- `docs/QUICK_START.md` - This file

## Key Features

✅ Auto-groups variants by parent_id  
✅ Detects up to 5 variation axes automatically  
✅ Each variant has unique SKU and axis signature  
✅ **Stores axes for LATER title generation** (not during import)  
✅ Handles product-level vs variant-level attributes  
✅ Flexible CSV structure (all variants OR parent + variants)  

## Common CSV Patterns

### Pattern 1: Apparel (Color + Size)
```csv
parent_id,sku,brand,color,size
SHIRT-001,SHIRT-001-RED-S,Nike,Red,Small
SHIRT-001,SHIRT-001-RED-M,Nike,Red,Medium
```
Result: 1 product, 2 variants, axes: color, size

### Pattern 2: Electronics (Color + Capacity)
```csv
parent_id,sku,brand,color,capacity
PHONE-001,PHONE-001-BLK-64,Samsung,Black,64GB
PHONE-001,PHONE-001-BLK-128,Samsung,Black,128GB
```
Result: 1 product, 2 variants, axes: color, capacity

### Pattern 3: Simple (No Variants)
```csv
parent_id,sku,brand,title
LAMP-001,LAMP-001,Philips,Desk Lamp
```
Result: 1 product, 1 variant, no axes

## Troubleshooting

**No axes detected?**
```python
# Manually mark columns
rule = ImportColumnRule.objects.get(
    product_import=import_obj,
    column_name='color'
)
rule.is_variation_axis = True
rule.axis_priority = 0
rule.save()
```

**Wrong grouping?**
- Check parent_id column has same value for related variants
- Verify column is detected as PRODUCT_KEY role

**Need help?**
- See `docs/PARENT_VARIANT_IMPORT.md` for detailed guide
- Run `python manage.py test_parent_variant_import` for working example

## Import vs Title Generation - Two Separate Steps

### Step 1: Import (Stores Structure)
```python
process_import(import_id)
# Stores: products, variants, axes, signatures
```

### Step 2: Title Generation (Done Later When Needed)
```python
generate_variant_title(variant)
# Uses stored axes to generate: "Running Shirt - Red Small"
```

---

## � Understanding What Import Does

**Read this first:** [What Import Does - Step by Step](WHAT_IMPORT_DOES.md)

This guide shows you **exactly** what gets created in the database when you import.

---

## �📋 What Exactly Happens During Import

When you run the import, the system **ONLY** does this:

### 1. Creates/Updates Products
- One `Product` record per unique `parent_id`
- Stores: code, brand, model, title, category
- Example: Product code `bike-001`

### 2. Creates/Updates Variants
- One `Variant` record per row (or per variant row)
- Each variant has: unique SKU, barcode, axis_signature
- Example: `BIKE-001-RED-M`, `BIKE-001-RED-L`, etc.

### 3. Detects and Stores Variation Axes
- Finds which attributes differentiate variants
- Stores in `ProductVariantAxis` (up to 5 axes per product)
- Example: color (position 0), size (position 1)

### 4. Creates Attribute Values
- `ProductAttributeValue` records for each attribute
- Stores at correct level (product vs variant)
- Marks variation axes with `is_axis=True`
- Example: color=Red, size=Medium, material=Aluminum

### 5. Generates Axis Signatures
- Each variant gets signature from axis values
- Example: `red:medium`, `blue:large`
- Used for quick variant lookup

**That's it! Nothing else happens during import.**

---

## 📥 Download Example CSV

### Example File: products_import_example.csv

We've created a sample CSV file you can use as a template. Download it here:
- **Location**: `docs/examples/products_import_example.csv`

This file shows both CSV structure options with real examples.

---

## ⚠️ Important: Import ONLY Upserts Data

The import process:
- ✅ **Creates** new products if they don't exist
- ✅ **Updates** existing products if code matches
- ✅ **Creates** new variants if SKU doesn't exist
- ✅ **Updates** existing variants if SKU matches
- ✅ **Stores** attributes and attribute values
- ✅ **Detects** and stores variation axes

**Does NOT:**
- ❌ Generate titles
- ❌ Create frontend UI
- ❌ Send to external systems
- ❌ Calculate prices or stock
- ❌ Validate business rules beyond basic structure

---

## 🎯 Complete Workflow

```
Step 1: IMPORT (This Step)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Upload CSV → Parse → Detect Axes → Store in Database
                                        ↓
                Products + Variants + Axes stored
                (Ready for next steps)

Step 2: TITLES (Later - When Needed)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Use stored axes → Generate titles
                    ↓
        "Mountain Bike Pro - Red Medium"

Step 3: FRONTEND (Later)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Use stored axes → Build variant selectors
                    ↓
        [Color: ▼Red] [Size: ▼Medium]

Step 4: API/EXPORT (Later)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Use stored data → Send to other systems
```

---

## What's Next?

1. ✅ **NOW - Import**: Upsert products, variants, attributes to database
2. 🔲 **Later - Titles**: Generate when you need them (display, SEO, export)
3. 🔲 **Later - Frontend**: Show variation axes for filtering/selection
4. 🔲 **Later - API**: Variant selection using axis values
