# Import Process Flow - What Happens When

## Two Separate Steps: Import vs Title Generation

```
┌─────────────────────────────────────────────────────────────────┐
│                     STEP 1: IMPORT (NOW)                        │
│                  Stores Structure Only                          │
└─────────────────────────────────────────────────────────────────┘

CSV File Input:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
parent_id │ sku           │ brand │ title      │ color │ size
──────────┼───────────────┼───────┼────────────┼───────┼──────
BIKE-001  │ BIKE-001-R-M  │ Trek  │ Bike Pro   │ Red   │ M
BIKE-001  │ BIKE-001-R-L  │ Trek  │ Bike Pro   │ Red   │ L
BIKE-001  │ BIKE-001-B-M  │ Trek  │ Bike Pro   │ Blue  │ M
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

                            ↓

System Groups & Detects:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Group by parent_id: BIKE-001
✓ Detect axes: color (2 values), size (2 values)
✓ Create axis signature for each variant
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

                            ↓

Database Storage:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┌─────────────────────────────────────────┐
│ Product: bike-001                       │
│   brand: Trek                           │
│   title: Bike Pro                       │
└─────────────────────────────────────────┘
         │
         ├── ProductVariantAxis[0]: color ◄── STORED FOR LATER!
         ├── ProductVariantAxis[1]: size  ◄── STORED FOR LATER!
         │
         ├── Variant: BIKE-001-R-M
         │     axis_signature: "red:m"  ◄── READY FOR LATER!
         │     └── Attributes:
         │           color=Red (is_axis=True)
         │           size=M (is_axis=True)
         │
         ├── Variant: BIKE-001-R-L
         │     axis_signature: "red:l"
         └── ...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

                     ❌ NO TITLES GENERATED YET!
                     
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                                                                        
                           TIME PASSES...                               
                                                                        
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


┌─────────────────────────────────────────────────────────────────┐
│              STEP 2: TITLE GENERATION (LATER)                   │
│               When You Need Titles                              │
└─────────────────────────────────────────────────────────────────┘

When You Need Titles:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Displaying products in catalog
- Generating SEO meta tags
- Creating product feeds (Google Shopping, etc.)
- Exporting to other systems
- Sending to frontend/API
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

                            ↓

Python Code:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
from catalog.services import generate_variant_title
variant = Variant.objects.get(sku='BIKE-001-R-M')
title = generate_variant_title(variant)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

                            ↓

Title Generation Uses Stored Axes:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Get base title: "Bike Pro"
2. Get axes from ProductVariantAxis:
   - Axis 0: color
   - Axis 1: size
3. Get axis values for this variant:
   - color: "Red"
   - size: "M"
4. Build title: "Bike Pro - Red M"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

                            ↓

Generated Titles:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ BIKE-001-R-M  →  "Bike Pro - Red M"
✓ BIKE-001-R-L  →  "Bike Pro - Red L"
✓ BIKE-001-B-M  →  "Bike Pro - Blue M"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Why Separate Steps?

### During Import:
**ONLY store the structure** - Fast and efficient
- Products and variants
- Parent-child relationships
- Which attributes are variation axes (color, size)
- Axis order/priority
- Axis signatures

### Later When Needed:
**Generate titles on demand** - Flexible and customizable
- Different templates for different uses
- Multi-language support
- SEO optimization
- Category-specific formats

## Example Use Cases

### Use Case 1: Product Catalog Display

```python
# In your view/API endpoint:
def get_product_detail(product_id):
    product = Product.objects.get(id=product_id)
    
    variants_data = []
    for variant in product.variants.all():
        variants_data.append({
            'sku': variant.sku,
            'title': generate_variant_title(variant),  # ← Generate here
            'price': variant.get_price(),
            'stock': variant.get_stock()
        })
    
    return {
        'product': product,
        'variants': variants_data
    }
```

### Use Case 2: SEO Meta Tags

```python
# In your template:
def get_seo_title(variant):
    title = generate_variant_title(variant)
    return f"Buy {title} | Your Store Name"

# Result: "Buy Bike Pro - Red M | Your Store Name"
```

### Use Case 3: Google Shopping Feed

```python
# When generating product feed:
from catalog.services import generate_variant_title_template

generator = generate_variant_title_template(
    product,
    template="{brand} {base_title} - {color} {size}"
)

for variant in product.variants.all():
    feed_title = generator(variant)
    # Result: "Trek Bike Pro - Red M"
```

### Use Case 4: Multi-Language

```python
# Different templates for different languages:
def generate_title_i18n(variant, lang='en'):
    if lang == 'en':
        template = "{base_title} - {color} {size}"
    elif lang == 'fr':
        template = "{base_title} - {color} {size}"  # French order
    elif lang == 'es':
        template = "{base_title} en {color} - Talla {size}"
    
    return generate_variant_title_template(variant.product, template)(variant)
```

## Summary

```
Import:           Store parent-child structure + axes
                         ↓
                  [Time passes...]
                         ↓
Title Generation: Use stored axes to generate titles when needed
```

**Key Benefits:**
- ✅ Import is fast (no complex processing)
- ✅ Titles are flexible (different templates)
- ✅ Can change title format without re-importing
- ✅ Supports multiple languages/formats
- ✅ No unnecessary computation during import
