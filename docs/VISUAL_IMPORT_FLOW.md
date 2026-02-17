# Import Mapping Flow - Visual Guide

## The Import Process

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          1. UPLOAD CSV FILE                             │
│                                                                         │
│  parent_id  │  sku       │  brand │  color │  size  │  price          │
│  ──────────────────────────────────────────────────────────────────    │
│  BIKE-001   │  SKU-001   │  Trek  │  Red   │  M     │  599.99         │
│  BIKE-001   │  SKU-002   │  Trek  │  Red   │  L     │  649.99         │
│  BIKE-001   │  SKU-003   │  Trek  │  Blue  │  M     │  599.99         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      2. ASSIGN CATEGORY                                 │
│                                                                         │
│  Select category: [Bicycles ▼]                                         │
│                                                                         │
│  This links all imported products to the right category                │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      3. MAP ATTRIBUTES                                  │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ 📘 Parent-Variant Product Import                                │  │
│  │                                                                  │  │
│  │  • Parent Product ID: Groups variants together                  │  │
│  │  • Variant SKU: Unique ID for each variant                      │  │
│  │  • Variation Axes: Auto-detected (color, size, etc.)            │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  File Column  │  Sample Data      │  Mapping                           │
│  ────────────────────────────────────────────────────────────────────  │
│  parent_id    │  BIKE-001         │  🔑 Parent Product ID              │
│  sku          │  SKU-001          │  Variant SKU                       │
│  brand        │  Trek             │  Product Brand                     │
│  color        │  Red, Blue        │  🔍 [Search: color] → ⚡ color     │
│  size         │  M, L             │  🔍 [Search: size]  → ⚡ size      │
│  price        │  599.99           │  🔍 [Search: price] → ⚡ price     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    4. AUTOMATIC DETECTION                               │
│                                                                         │
│  System analyzes data and detects:                                     │
│                                                                         │
│  ✓ Variation Axes:                                                     │
│    - color (2 values: Red, Blue)    Priority: 1                        │
│    - size  (2 values: M, L)         Priority: 2                        │
│                                                                         │
│  ✓ Parent-Variant Groups:                                              │
│    - BIKE-001 → 3 variants                                             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    5. STORAGE IN DATABASE                               │
│                                                                         │
│  Products Table:                                                        │
│  ┌────────────────────────────────────────────────┐                    │
│  │ id: 1                                          │                    │
│  │ code: BIKE-001                                 │                    │
│  │ brand: Trek                                    │                    │
│  │ default_label: Mountain Bike                  │                    │
│  └────────────────────────────────────────────────┘                    │
│                                                                         │
│  Variants Table:                                                        │
│  ┌────────────────────────────────────────────────┐                    │
│  │ id: 1, product_id: 1, sku: SKU-001            │                    │
│  │ → Attributes: {color: Red, size: M}            │                    │
│  ├────────────────────────────────────────────────┤                    │
│  │ id: 2, product_id: 1, sku: SKU-002            │                    │
│  │ → Attributes: {color: Red, size: L}            │                    │
│  ├────────────────────────────────────────────────┤                    │
│  │ id: 3, product_id: 1, sku: SKU-003            │                    │
│  │ → Attributes: {color: Blue, size: M}           │                    │
│  └────────────────────────────────────────────────┘                    │
│                                                                         │
│  ProductVariantAxis Table:                                             │
│  ┌────────────────────────────────────────────────┐                    │
│  │ product_id: 1                                  │                    │
│  │ attribute_code: color, priority: 1             │                    │
│  │ attribute_code: size,  priority: 2             │                    │
│  └────────────────────────────────────────────────┘                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                  6. LATER: TITLE GENERATION                             │
│                                                                         │
│  Using stored variation axes to generate titles:                       │
│                                                                         │
│  Template: "{brand} {default_label} - {color} {size}"                  │
│                                                                         │
│  Generated Titles:                                                      │
│  - Trek Mountain Bike - Red M                                          │
│  - Trek Mountain Bike - Red L                                          │
│  - Trek Mountain Bike - Blue M                                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Key Features of the Mapping UI

### 🔍 Search Box
Each column has its own search field in the dropdown:
```
┌──────────────────────────────────────┐
│ 🔎 Search attributes...              │  ← Type here to filter
├──────────────────────────────────────┤
│ ⚡ color (choice)                    │
│ ⚡ size (choice)                     │
│ ⚡ material (text)                   │
└──────────────────────────────────────┘
```

### 🔑 Special Fields
Marked with icons for easy identification:
- `🔑 Parent Product ID` - Groups variants
- `⚡ color`, `⚡ size` - Attributes

### ✅ Variation Axis Detection
Table shows which columns will be variation axes:
```
File Column  │  Mapping         │  Variation Axis
─────────────────────────────────────────────────
color        │  ⚡ color        │  ✓ Variation axis
size         │  ⚡ size         │  ✓ Variation axis
price        │  ⚡ price        │  
```

---

## What's Different from Before?

### OLD BEHAVIOR ❌
1. System tries to auto-suggest mappings
2. Suggestions often wrong (language mismatch, wrong attributes)
3. User has to manually fix all wrong suggestions
4. No search - scroll through long lists
5. No clear explanation of what fields do

### NEW BEHAVIOR ✅
1. **No auto-suggestions** - you're in control
2. **Search box** - type to filter and find
3. **Clear instructions** - help panel at top
4. **Visual indicators** - 🔑 for parent ID, ⚡ for attributes
5. **Variation axis column** - see what will be detected
6. **Better table** - 5 columns with all info needed

---

## Tips for Successful Mapping

1. **Start with Parent Product ID**
   - This is the most important column
   - Map it first to see grouping structure

2. **Then map Variant SKU**
   - Ensures each variant has unique identifier

3. **Map product fields next**
   - Brand, model, title - same for all variants

4. **Finally map variant attributes**
   - Use search to find: color, size, price, etc.
   - System auto-detects which are variation axes

5. **Review variation axes**
   - Check the "Variation Axis" column
   - Should show attributes that differ between variants

6. **Create new if needed**
   - Check "Create New" for attributes not in system
   - System creates them during import

---

## Common Patterns

### Pattern 1: Parent ID Column Exists
```
parent_id → 🔑 Parent Product ID
sku       → Variant SKU
color     → ⚡ color (variation axis)
size      → ⚡ size (variation axis)
```

### Pattern 2: No Parent ID (Group by Product Code)
```
product_code → Product Code (system groups by this)
variant_sku  → Variant SKU
color        → ⚡ color (variation axis)
finish       → ⚡ finish (variation axis)
```

### Pattern 3: Multilingual Attributes
```
couleur      → ⚡ color (search "color")
taille       → ⚡ size (search "size")
prix         → ⚡ price (search "price")
```

