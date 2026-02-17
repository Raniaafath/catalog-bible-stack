# Current Architecture Explained

## The Confusion: Product vs Variant

You're right to be confused! The current naming is misleading:

- **"Product"** in the database = Actually a **Group/Family** (contains multiple variants)
- **"Variant"** in the database = Actually the **individual sellable item** (what most people call "product")

## Current Structure (What We Have)

```
┌─────────────────────────────────────────────────────────────┐
│ Product (Group/Family)                                       │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ code: "tr-can-90180-7040-acr-pir-exg-pos"                │ │
│ │ brand: "Hydroline"                                        │ │
│ │ model: "..."                                              │ │
│ │                                                             │ │
│ │ ┌─────────────────────────────────────────────────────┐  │ │
│ │ │ ChannelVariantAxis (Marketplace Axes)               │  │ │
│ │ │ - Product + Channel → Variation Axes                │  │ │
│ │ │   Example: Product + Shopify → [color, size]        │  │ │
│ │ │   Example: Product + eBay → [color, size, material]│ │ │
│ │ └─────────────────────────────────────────────────────┘  │ │
│ │                                                             │ │
│ │ ┌─────────────────────────────────────────────────────┐  │ │
│ │ │ ChannelListing (Marketplace Listings)               │  │ │
│ │ │ - Product + Channel → Listing Groups                │  │ │
│ │ │   Example: Product + Shopify → Default Listing      │  │ │
│ │ └─────────────────────────────────────────────────────┘  │ │
│ │                                                             │ │
│ │ ┌─────────────────────────────────────────────────────┐  │ │
│ │ │ Variants (Children)                                 │  │ │
│ │ │                                                       │  │ │
│ │ │ Variant 1: SKU "TR-CAN-90180-7040-ACR-PIR-EXG-POS"  │  │ │
│ │ │   └─ Attributes (18 attributes)                     │  │ │
│ │ │      - couleur-principale: gris                      │  │ │
│ │ │      - matiere-principale-du-produit: acrylique      │  │ │
│ │ │      - dimensions-l-x-l-en-cm: 90-x-180              │  │ │
│ │ │      - ... (15 more)                                 │  │ │
│ │ │                                                       │  │ │
│ │ │ Variant 2: SKU "TR-CAN-90180-7040-RSN-LIS-CNL-POS"  │  │ │
│ │ │   └─ Attributes (18 attributes)                       │  │ │
│ │ │      - couleur-principale: gris                      │  │ │
│ │ │      - matiere-principale-du-produit: resine         │  │ │
│ │ │      - dimensions-l-x-l-en-cm: 90-x-180              │  │ │
│ │ │      - ... (15 more)                                 │  │ │
│ │ └─────────────────────────────────────────────────────┘  │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Database Relationships

### 1. Product (Group) → Variants
```sql
Product (id: 560, code: "tr-can-90180-7040-acr-pir-exg-pos")
  └─ Variant (id: 557, product_id: 560, sku: "TR-CAN-90180-7040-ACR-PIR-EXG-POS")
  └─ Variant (id: 556, product_id: 560, sku: "TR-CAN-90180-7040-RSN-LIS-CNL-POS")
```

### 2. Variant → Attributes (via ProductAttributeValue)
```sql
Variant (id: 557)
  └─ ProductAttributeValue (variant_id: 557, attribute_id: 157, attribute_value_id: 187)
      ├─ Attribute (id: 157, code: "couleur-principale")
      └─ AttributeValue (id: 187, code: "gris")
```

### 3. Product (Group) → Channels (Marketplaces)
```sql
Product (id: 560)
  └─ ChannelVariantAxis (product_id: 560, channel_id: 1, attribute_id: 157)
      ├─ Channel (id: 1, code: "shopify")
      └─ Attribute (id: 157, code: "couleur-principale")
```

### 4. Product (Group) → Channel Listings
```sql
Product (id: 560)
  └─ ChannelListing (product_id: 560, channel_id: 1, locale_id: 1)
      └─ ChannelListingMap (listing_id: X, variant_id: 557, channel_id: 1)
```

## Why We Have Both Product and Variant

**Product (Group)** is needed because:
1. **Shared attributes**: Brand, model, series are the same for all variants
2. **Marketplace configuration**: Variation axes are defined per Product + Channel
3. **Listing management**: Listings are created per Product + Channel
4. **Grouping logic**: Variants that share attributes are grouped together

**Variant** is needed because:
1. **Individual SKUs**: Each variant is a unique sellable item
2. **Variant-specific attributes**: Color, size, material differ per variant
3. **Source data**: Each variant has its own source_title, source_description, etc.

## What We Changed in Frontend

To make it clearer, we've updated the frontend to use "Group" terminology:

- ✅ Navigation menu: "Products" → "Groups"
- ✅ Page titles: "Products" → "Product Groups"
- ✅ Descriptions: Added explanation that groups contain variants
- ✅ Labels: "Add Product" → "Add Group"

**Backend still uses "Product"** (to avoid breaking changes), but the UI now clearly shows it's a "Group".

## Your Suggestion: Full Rename

You suggested:
- Create "Groups" model
- Groups have variants
- Groups have marketplace/channel
- Groups have axes/variation axes
- Remove Product-Variant relationship

**This is essentially what we already have!** The current "Product" IS a group. We just need better naming.

## Recommendation

**Option 1: Frontend-only rename (DONE ✅)**
- Keep backend as `Product` (less breaking)
- Frontend shows "Groups" (clearer for users)
- Add documentation explaining Product = Group

**Option 2: Full backend rename (Future)**
- Rename `Product` → `Group` in database
- Update all code
- More work but cleaner long-term

For now, **Option 1 is implemented** - the frontend now clearly shows "Groups" instead of "Products", making it obvious that:
- **Groups** = Containers that hold variants
- **Groups** = Have marketplaces/channels linked
- **Groups** = Have variation axes defined
- **Variants** = Individual items with attributes
