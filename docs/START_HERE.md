# START HERE - Parent-Variant Import System

## 🎯 What You're Doing

You're importing a CSV file with products and their variants (like different colors/sizes of the same product). The system will:

1. ✅ Group variants under parent products
2. ✅ Detect which attributes differentiate variants (color, size, etc.)
3. ✅ Store everything in the database
4. ❌ **NOT** generate titles yet (that's a separate step later)

---

## � Documentation Quick Links

- **[Attribute Research Features](ATTRIBUTE_RESEARCH_FEATURES.md)** - Multi-field search & tooltips in the mapping UI
- **[Frontend Mapping Guide](FRONTEND_MAPPING_GUIDE.md)** - How to use the mapping UI
- **[Quick Reference](QUICK_REFERENCE.md)** - Cheat sheet for mapping
- **[CSV Structure Examples](CSV_STRUCTURE_EXAMPLES.md)** - See different CSV format options
- **[Quick Start Guide](QUICK_START.md)** - Step-by-step tutorial
- **[What Import Does](WHAT_IMPORT_DOES.md)** - Technical details

---

## �📥 Step 1: Download Example CSV

**Before you import your data, see how it should look:**

📄 **[Download: products_import_example.csv](examples/products_import_example.csv)**

This file contains 3 sample products with 14 variants - open it to understand the structure!

**Example structure:**
```csv
parent_id,sku,brand,title,color,size,price
BIKE-001,BIKE-001-RED-M,Trek,Mountain Bike,Red,Medium,599.99
BIKE-001,BIKE-001-RED-L,Trek,Mountain Bike,Red,Large,649.99
BIKE-001,BIKE-001-BLUE-M,Trek,Mountain Bike,Blue,Medium,599.99
```

**Key columns:**
- `parent_id` - Groups variants together (all with "BIKE-001" = one product)
- `sku` - Unique ID for each variant
- `color`, `size` - Variation axes (automatically detected)

---

## 🚀 Step 2: Run Migration

```bash
python manage.py migrate importer
```

This adds the necessary database fields for parent-child relationships.

---

## 📤 Step 3: Import Your CSV

### Using Python:
```python
from importer.models import ProductImport
from importer.services import parse_import, process_import

# 1. Upload file
import_obj = ProductImport.objects.create(
    source_file=your_csv_file,
    status='uploaded'
)

# 2. Parse (reads CSV)
parse_import(import_obj.id)

# 3. Process (creates products, variants, axes)
stats = process_import(import_obj.id)

print(stats)
# Shows: products created, variants created, axes detected
```

### Using Admin Interface:
1. Go to Django Admin → Product Imports
2. Upload your CSV file
3. Click "Parse" then "Process"

---

## ✅ Step 4: Verify What Was Created

```python
from catalog.models import Product, ProductVariantAxis

# Check products
product = Product.objects.get(code='bike-001')
print(f"Variants: {product.variants.count()}")  # 3

# Check variation axes (THESE ARE STORED FOR LATER!)
axes = product.variant_axes.order_by('position')
for axis in axes:
    print(f"Axis {axis.position}: {axis.attribute.code}")
# Output: Axis 0: color
#         Axis 1: size
```

---

## 💾 What Got Stored in Database

After importing the example CSV above:

```
Product: bike-001
  ├─ Brand: Trek
  ├─ Title: Mountain Bike
  ├─ ProductVariantAxis[0]: color  ← Stored for later title generation!
  ├─ ProductVariantAxis[1]: size   ← Stored for later title generation!
  └─ Variants:
      ├─ BIKE-001-RED-M  (axis_signature: "red:medium")
      ├─ BIKE-001-RED-L  (axis_signature: "red:large")
      └─ BIKE-001-BLUE-M (axis_signature: "blue:medium")
```

**Each variant has:**
- SKU (unique identifier)
- Axis signature (for quick lookup)
- Attribute values (color, size, price, etc.)

**Variation axes are marked** with `is_axis=True` so you can use them later!

---

## 🔮 What Happens Next (LATER Steps)

### When You Need Titles:
Use the **Listing Groups** workflow: create a listing group, set axes, create a template, then generate titles via `POST /api/v1/channel-listings/{id}/generate-titles/`. See [LISTING_GROUP_WORKFLOW.md](LISTING_GROUP_WORKFLOW.md).

### When Building Frontend:
- Show variation axes as dropdowns/filters
- Use axis signatures to find variants
- Display generated titles in product listings

### When Exporting:
- Generate titles for product feeds
- Use axes for filtering/grouping

---

## 📚 Full Documentation

**Quick References:**
- **[QUICK_START.md](QUICK_START.md)** - Detailed quick start
- **[WHAT_IMPORT_DOES.md](WHAT_IMPORT_DOES.md)** - See exactly what gets created
- **[examples/README.md](examples/README.md)** - Example CSV files explained

**Architecture (product family vs listing group):**
- **[GROUPING_AND_MARKETPLACE_AXES.md](GROUPING_AND_MARKETPLACE_AXES.md)** - Two levels of grouping and variation axis resolution

**Detailed Guides:**
- **[CSV_STRUCTURE_EXAMPLES.md](CSV_STRUCTURE_EXAMPLES.md)** - All CSV format options
- **[LISTING_GROUP_WORKFLOW.md](LISTING_GROUP_WORKFLOW.md)** - Full title generation workflow after import
- **[SIMPLE_GROUPING_WORKFLOW.md](SIMPLE_GROUPING_WORKFLOW.md)** - Complete simple workflow guide (Recommended)

---

## ❓ Common Questions

**Q: Do I need to structure my CSV with a parent row?**  
A: No! Both formats work:
- All rows = variants (simpler, just repeat shared data)
- Parent row + variant rows (more structured)

**Q: Will titles be generated during import?**  
A: No! Import only stores structure. Generate titles later when you need them.

**Q: What if I have no variations (simple products)?**  
A: Works fine! Each product will have 1 variant, no axes detected.

**Q: Can I have more than 5 variation axes?**  
A: System stores top 5 by priority. Most products have 1-3 axes anyway.

**Q: How do I mark specific columns as axes?**  
A: Set `is_variation_axis=True` on column rules, or let the system auto-detect.

---

## 🎯 Summary

1. **Download** example CSV to see structure
2. **Run** migration
3. **Import** your CSV file
4. **Verify** products, variants, and axes were created
5. **Later** generate titles when you need them

**The import step ONLY stores the structure in the database. Everything else happens later!**

Ready to start? Download [products_import_example.csv](examples/products_import_example.csv)! 🚀
