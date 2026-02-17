# IMPORT STEP - What You're Actually Doing

## 📥 Step 1: Prepare Your CSV File

Download one of our examples:
- [products_import_example.csv](examples/products_import_example.csv) - Simpler format
- [products_import_parent_variant.csv](examples/products_import_parent_variant.csv) - Structured format

Or create your own following the same structure.

---

## 🔄 Step 2: Run the Import

```python
from importer.models import ProductImport
from importer.services import parse_import, process_import

# 1. Upload file
import_obj = ProductImport.objects.create(
    source_file=your_csv_file,
    status='uploaded'
)

# 2. Parse CSV (reads file, creates ImportRow records)
parse_import(import_obj.id)

# 3. Process Import (creates products, variants, axes)
stats = process_import(import_obj.id)

print(stats)
# Output shows what was created
```

---

## 💾 Step 3: What Gets Stored in Database

### Input CSV (Example):
```csv
parent_id,sku,brand,title,color,size,price
BIKE-001,BIKE-001-RED-M,Trek,Bike Pro,Red,Medium,599.99
BIKE-001,BIKE-001-RED-L,Trek,Bike Pro,Red,Large,649.99
BIKE-001,BIKE-001-BLUE-M,Trek,Bike Pro,Blue,Medium,599.99
```

### Output Database (What Gets Created):

```
┌──────────────────────────────────────────────┐
│ 1. Product Table                             │
├──────────────────────────────────────────────┤
│ id: 1                                        │
│ code: "bike-001"                             │
│ brand: "Trek"                                │
│ default_label: "Bike Pro"                    │
│ product_type_id: ...                         │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│ 2. ProductVariantAxis Table                  │
├──────────────────────────────────────────────┤
│ product_id: 1                                │
│ attribute_id: 5 (color)                      │
│ position: 0          ◄── First axis          │
├──────────────────────────────────────────────┤
│ product_id: 1                                │
│ attribute_id: 6 (size)                       │
│ position: 1          ◄── Second axis         │
└──────────────────────────────────────────────┘
        ▲
        │
    STORED FOR LATER TITLE GENERATION!

┌──────────────────────────────────────────────┐
│ 3. Variant Table                             │
├──────────────────────────────────────────────┤
│ product_id: 1                                │
│ sku: "BIKE-001-RED-M"                        │
│ axis_signature: "red:medium"  ◄── Generated  │
│ barcode: null                                │
├──────────────────────────────────────────────┤
│ product_id: 1                                │
│ sku: "BIKE-001-RED-L"                        │
│ axis_signature: "red:large"                  │
├──────────────────────────────────────────────┤
│ product_id: 1                                │
│ sku: "BIKE-001-BLUE-M"                       │
│ axis_signature: "blue:medium"                │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│ 4. ProductAttributeValue Table               │
├──────────────────────────────────────────────┤
│ variant_id: 1 (BIKE-001-RED-M)               │
│ attribute_id: 5 (color)                      │
│ attribute_value_id: 10 (red)                 │
│ is_axis: TRUE         ◄── Variation axis!    │
├──────────────────────────────────────────────┤
│ variant_id: 1 (BIKE-001-RED-M)               │
│ attribute_id: 6 (size)                       │
│ attribute_value_id: 15 (medium)              │
│ is_axis: TRUE         ◄── Variation axis!    │
├──────────────────────────────────────────────┤
│ variant_id: 1 (BIKE-001-RED-M)               │
│ attribute_id: 7 (price)                      │
│ value_number: 599.99                         │
│ is_axis: FALSE        ◄── Not a variation    │
└──────────────────────────────────────────────┘
... (more rows for other variants)
```

---

## ✅ Step 4: Verify What Was Created

```python
from catalog.models import Product, ProductVariantAxis

# Check the product
product = Product.objects.get(code='bike-001')
print(f"Product: {product.code}")
print(f"Brand: {product.brand}")
print(f"Variants count: {product.variants.count()}")  # 3

# Check variation axes (STORED FOR LATER!)
axes = product.variant_axes.order_by('position')
for axis in axes:
    print(f"Axis {axis.position}: {axis.attribute.code}")
# Output:
#   Axis 0: color
#   Axis 1: size

# Check variants
for variant in product.variants.all():
    print(f"Variant: {variant.sku}")
    print(f"  Signature: {variant.axis_signature}")
    
# Output:
#   Variant: BIKE-001-RED-M
#     Signature: red:medium
#   Variant: BIKE-001-RED-L
#     Signature: red:large
#   Variant: BIKE-001-BLUE-M
#     Signature: blue:medium
```

---

## 🚫 What Did NOT Happen

During import, the system did **NOT**:

❌ Generate variant titles  
❌ Create any frontend UI  
❌ Send data to external systems  
❌ Calculate prices or discounts  
❌ Check inventory  
❌ Create SEO meta tags  
❌ Generate product feeds  

**All of that comes later!**

---

## 🎯 What You Can Do Now (After Import)

### 1. Query Products and Variants
```python
from catalog.models import Product, Variant

# Get all products
products = Product.objects.all()

# Get variants for a product
product = Product.objects.get(code='bike-001')
variants = product.variants.all()
```

### 2. Find Variants by Axis Signature
```python
# Find the Red + Medium variant
variant = Variant.objects.get(
    product__code='bike-001',
    axis_signature='red:medium'
)
```

### 3. Get Variation Axes
```python
# Get stored axes (for later title generation)
product = Product.objects.get(code='bike-001')
axes = product.variant_axes.order_by('position')

for axis in axes:
    print(f"{axis.position}: {axis.attribute.code}")
```

---

## 📝 Next Steps (Do These LATER)

### When You Need Titles:
```python
from catalog.services import generate_variant_title

variant = Variant.objects.get(sku='BIKE-001-RED-M')
title = generate_variant_title(variant)
# Uses stored axes to generate: "Bike Pro - Red Medium"
```

### When Building Frontend:
```javascript
// API returns variation axes
{
  "variation_axes": [
    {"code": "color", "position": 0, "values": ["Red", "Blue"]},
    {"code": "size", "position": 1, "values": ["Medium", "Large"]}
  ]
}

// Build variant selector UI:
// [Color: ▼Red] [Size: ▼Medium]
```

### When Exporting:
```python
# Use axes to generate titles for product feeds
for variant in product.variants.all():
    title = generate_variant_title(variant)
    # Export to Google Shopping, etc.
```

---

## 📊 Summary: Import = Store Structure Only

```
CSV File
   ↓
Import Process
   ↓
Database Tables Populated:
   ├─ Product (parent products)
   ├─ Variant (individual SKUs)
   ├─ ProductVariantAxis (which axes to use) ◄─ KEY!
   └─ ProductAttributeValue (actual data)
   ↓
Ready for next steps:
   ├─ Title generation
   ├─ Frontend display
   └─ API/exports
```

**Import stores the structure. Everything else happens later when you need it!**

---

## ⚡ Quick Reference

**What import does:**
- ✅ Creates products, variants, axes
- ✅ Stores axis order (position 0, 1, 2...)
- ✅ Marks variation attributes (is_axis=True)
- ✅ Generates axis signatures

**What to do after import:**
- Use `ProductVariantAxis` for title generation
- Use `axis_signature` for variant lookup
- Use `is_axis=True` to identify variation attributes
- Generate titles on-demand when displaying products

**Example CSV files to download:**
- `docs/examples/products_import_example.csv`
- `docs/examples/products_import_parent_variant.csv`

**You're ready to import!** 🚀
