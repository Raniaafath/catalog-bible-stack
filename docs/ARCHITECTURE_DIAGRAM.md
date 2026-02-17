# System Architecture: Parent-Variant Import

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        1. CSV INPUT                              │
│                                                                  │
│  parent_id │ sku           │ brand │ color │ size  │ price     │
│  ──────────┼───────────────┼───────┼───────┼───────┼──────     │
│  BIKE-001  │ BIKE-001-R-M  │ Trek  │ Red   │ M     │ 599.99   │
│  BIKE-001  │ BIKE-001-R-L  │ Trek  │ Red   │ L     │ 649.99   │
│  BIKE-001  │ BIKE-001-B-M  │ Trek  │ Blue  │ M     │ 599.99   │
│  BIKE-001  │ BIKE-001-B-L  │ Trek  │ Blue  │ L     │ 649.99   │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                   2. COLUMN DETECTION                            │
│                                                                  │
│  parent_id    →  PRODUCT_KEY   (groups variants)                │
│  sku          →  VARIANT_KEY   (unique identifier)              │
│  brand        →  BRAND         (product field)                  │
│  color        →  ATTRIBUTE     (variation axis candidate)       │
│  size         →  ATTRIBUTE     (variation axis candidate)       │
│  price        →  ATTRIBUTE     (variant-level)                  │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                3. VARIATION AXIS DETECTION                       │
│                                                                  │
│  Analyze columns across variants in each parent group:          │
│                                                                  │
│  color: [Red, Red, Blue, Blue]  → 2 unique values ✓            │
│  size:  [M, L, M, L]            → 2 unique values ✓            │
│  price: [599.99, 649.99, ...]   → variant-level, not axis      │
│  brand: [Trek, Trek, Trek, ...]  → 1 unique value ✗            │
│                                                                  │
│  Selected axes: color (priority 0), size (priority 1)           │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                    4. DATABASE STRUCTURE                         │
│                                                                  │
│  ┌─────────────────────────────────────────┐                   │
│  │ Product: bike-001                       │                   │
│  │   code: bike-001                        │                   │
│  │   brand: Trek                           │                   │
│  │   product_type: bikes                   │                   │
│  └─────────────────────────────────────────┘                   │
│           │                                                      │
│           ├── ProductVariantAxis[0]: color                      │
│           │                                                      │
│           ├── ProductVariantAxis[1]: size                       │
│           │                                                      │
│           ├── Variant: BIKE-001-R-M                            │
│           │     sku: BIKE-001-R-M                              │
│           │     axis_signature: "red:m"                         │
│           │     └── ProductAttributeValue                       │
│           │           attribute: color = Red (is_axis=True)    │
│           │           attribute: size = M (is_axis=True)       │
│           │           attribute: price = 599.99                │
│           │                                                      │
│           ├── Variant: BIKE-001-R-L                            │
│           │     sku: BIKE-001-R-L                              │
│           │     axis_signature: "red:l"                         │
│           │     └── ...                                         │
│           │                                                      │
│           └── ... (2 more variants)                             │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                    5. TITLE GENERATION                           │
│                                                                  │
│  get_variant_axes(product)                                      │
│    → [color, size]  (ordered by position)                      │
│                                                                  │
│  get_axis_values(variant)                                       │
│    → {color: "Red", size: "M"}                                 │
│                                                                  │
│  generate_title(variant)                                        │
│    → "Mountain Bike Pro - Red M"                               │
│                                                                  │
│  Results:                                                        │
│    BIKE-001-R-M  → "Mountain Bike Pro - Red M"                │
│    BIKE-001-R-L  → "Mountain Bike Pro - Red L"                │
│    BIKE-001-B-M  → "Mountain Bike Pro - Blue M"               │
│    BIKE-001-B-L  → "Mountain Bike Pro - Blue L"               │
└─────────────────────────────────────────────────────────────────┘
```

## Entity Relationship Diagram

```
┌──────────────────┐
│   ProductType    │
│                  │
│  code            │
│  default_label   │
└────────┬─────────┘
         │
         │ 1
         │
         │ N
┌────────▼─────────┐        1      ┌─────────────────────┐
│     Product      ├───────────────►│ ProductVariantAxis  │
│                  │                │                     │
│  code            │                │  attribute_id       │
│  brand           │                │  position (0-4)     │
│  product_type_id │                │  label_override     │
└────────┬─────────┘                └─────────────────────┘
         │
         │ 1
         │
         │ N
┌────────▼─────────┐
│     Variant      │
│                  │
│  sku             │
│  product_id      │
│  axis_signature  │ ← Generated from axes (e.g., "red:m")
│  barcode         │
└────────┬─────────┘
         │
         │ 1
         │
         │ N
┌────────▼──────────────────┐
│ ProductAttributeValue     │
│                           │
│  variant_id               │
│  attribute_id             │
│  attribute_value_id       │
│  value_text / number      │
│  is_axis (True/False)     │ ← Marks variation axes
└───────────────────────────┘
```

## Processing Flow

```
┌─────────────┐
│ Upload CSV  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Parse CSV  │──────► Create ImportRow for each row
└──────┬──────┘        Store raw data in JSON
       │
       ▼
┌──────────────────┐
│ Detect Columns   │──────► Create ImportColumnRule
└──────┬───────────┘        Auto-assign roles (PRODUCT_KEY, VARIANT_KEY, etc.)
       │
       ▼
┌──────────────────┐
│ Configure Axes   │──────► Set is_variation_axis = True
│   (Optional)     │        Set axis_priority (0-4)
└──────┬───────────┘        Set variant_level = True
       │
       ▼
┌──────────────────┐
│ Group by Parent  │──────► Group ImportRows by PRODUCT_KEY value
└──────┬───────────┘        Each group = 1 parent product
       │
       ▼
┌──────────────────┐
│  Detect Axes     │──────► For each parent group:
└──────┬───────────┘          - Find columns with 2-20 unique values
       │                      - Score by: is_variation_axis, common names, diversity
       │                      - Select top 5
       ▼
┌──────────────────┐
│ Create Products  │──────► 1 Product per parent group
└──────┬───────────┘        Store brand, model, etc.
       │
       ▼
┌──────────────────┐
│  Store Axes      │──────► Create ProductVariantAxis records
└──────┬───────────┘        Link to Attribute, set position
       │
       ▼
┌──────────────────┐
│ Create Variants  │──────► 1 Variant per ImportRow
└──────┬───────────┘        Generate axis_signature from axis values
       │
       ▼
┌──────────────────┐
│ Store Attributes │──────► Create ProductAttributeValue
└──────┬───────────┘          - Product-level: shared attributes
       │                      - Variant-level: unique attributes
       │                      - Mark axes with is_axis=True
       ▼
┌──────────────────┐
│    Complete!     │
└──────────────────┘
```

## Variation Axis Priority Scoring

```
For each column:

  Base Score = 0

  IF is_variation_axis == True:
    Score += 1000 + axis_priority
    
  IF column_name in [color, size, capacity, material, ...]:
    Score += 100
    
  Unique_Values = count(distinct values)
  IF 2 <= Unique_Values <= 20:
    Score += (20 - Unique_Values)

  Sort all columns by Score DESC
  Take top 5 as variation axes
```

## Example Scoring

```
Column    │ is_axis │ Common │ Unique │ Score │ Selected?
──────────┼─────────┼────────┼────────┼───────┼──────────
color     │ True(0) │ Yes    │ 2      │ 1118  │ ✓ Axis 0
size      │ True(1) │ Yes    │ 2      │ 1119  │ ✓ Axis 1
brand     │ False   │ Yes    │ 1      │ 100   │ ✗
price     │ False   │ No     │ 4      │ 16    │ ✗
barcode   │ False   │ No     │ 4      │ 16    │ ✗
```

## Title Generation Templates

### Default Template
```
{base_title} - {axis_0} {axis_1} {axis_2}...
```

### Custom Templates
```python
# Template 1: Comma-separated
"{base_title} ({color}, {size})"
→ "Mountain Bike Pro (Red, Medium)"

# Template 2: With labels
"{base_title} in {color} - Size {size}"
→ "Mountain Bike Pro in Red - Size Medium"

# Template 3: SEO-friendly
"{base_title} | {color} | {size}"
→ "Mountain Bike Pro | Red | Medium"
```

## API Response Structure

```json
{
  "product": {
    "code": "bike-001",
    "brand": "Trek",
    "title": "Mountain Bike Pro",
    "variation_axes": [
      {
        "code": "color",
        "position": 0,
        "label": "Color",
        "values": ["Red", "Blue"]
      },
      {
        "code": "size",
        "position": 1,
        "label": "Size",
        "values": ["Medium", "Large"]
      }
    ],
    "variants": [
      {
        "sku": "BIKE-001-R-M",
        "title": "Mountain Bike Pro - Red Medium",
        "axis_signature": "red:medium",
        "axis_values": {
          "color": "Red",
          "size": "Medium"
        },
        "price": "599.99",
        "barcode": "123456001"
      }
    ]
  }
}
```

## Frontend Usage

### Variant Selector
```javascript
// Render variation selectors
axes.forEach(axis => {
  const selector = createSelect(axis.label);
  axis.values.forEach(value => {
    selector.addOption(value);
  });
});

// When user selects color="Red", size="Medium"
const signature = `${slugify(color)}:${slugify(size)}`;
const variant = variants.find(v => v.axis_signature === signature);
```

### Product Filters
```javascript
// Filter by axis values
GET /api/products?color=red&size=large

// Backend query
Variant.objects.filter(
  attribute_values__attribute__code='color',
  attribute_values__attribute_value__code='red'
).filter(
  attribute_values__attribute__code='size',
  attribute_values__attribute_value__code='large'
)
```

## Database Queries

### Get all variants with axis values
```python
from catalog.models import Product

product = Product.objects.get(code='bike-001')
axes = product.variant_axes.order_by('position')

for variant in product.variants.prefetch_related('attribute_values'):
    axis_values = {}
    for axis in axes:
        pav = variant.attribute_values.filter(
            attribute=axis.attribute,
            is_axis=True
        ).first()
        if pav:
            axis_values[axis.attribute.code] = pav.get_display_value()
    
    print(f"{variant.sku}: {axis_values}")
```

### Find variant by axis combination
```python
# Find "Red" + "Medium"
variant = Variant.objects.get(
    product__code='bike-001',
    axis_signature='red:medium'
)
```

### Get all products with specific axis value
```python
# All products with "Red" variants
products = Product.objects.filter(
    variants__attribute_values__attribute__code='color',
    variants__attribute_values__attribute_value__code='red'
).distinct()
```
