# Product → Group Rename Proposal

## Current Confusion

The current naming is confusing:
- **Product** = Actually a **Group/Family** (contains multiple variants)
- **Variant** = Actually the **individual sellable item** (what most people call "product")

This causes confusion because:
1. In e-commerce, "Product" usually means the individual item
2. Users see "Products" in the UI but it's really showing groups/families
3. The relationship isn't clear: Why do we need both Product and Variant?

## Current Architecture

```
Product (Group/Family)
  ├─ code: "tr-can-90180-7040-acr-pir-exg-pos"
  ├─ brand, model, series (shared attributes)
  ├─ ProductVariantAxis (default axes)
  ├─ ChannelVariantAxis (axes per marketplace)
  ├─ ChannelListing (listings per marketplace)
  └─ Variants (children)
      ├─ Variant 1: SKU "TR-CAN-90180-7040-ACR-PIR-EXG-POS"
      │   └─ Attributes (18 attributes linked via ProductAttributeValue)
      └─ Variant 2: SKU "TR-CAN-90180-7040-RSN-LIS-CNL-POS"
          └─ Attributes (18 attributes linked via ProductAttributeValue)
```

## Proposed Architecture (Rename)

```
Group (Product Family)
  ├─ code: "tr-can-90180-7040-acr-pir-exg-pos"
  ├─ brand, model, series (shared attributes)
  ├─ GroupVariantAxis (default axes)
  ├─ ChannelVariantAxis (axes per marketplace) - Group + Channel
  ├─ ChannelListing (listings per marketplace) - Group + Channel
  └─ Variants (children)
      ├─ Variant 1: SKU "TR-CAN-90180-7040-ACR-PIR-EXG-POS"
      │   └─ Attributes (18 attributes linked via ProductAttributeValue)
      └─ Variant 2: SKU "TR-CAN-90180-7040-RSN-LIS-CNL-POS"
          └─ Attributes (18 attributes linked via ProductAttributeValue)
```

## Why This Makes Sense

1. **Clearer naming**: "Group" clearly indicates it's a container
2. **Better UX**: Frontend can show "Groups" and "Variants" clearly
3. **Logical structure**: 
   - Groups contain variants
   - Groups have marketplaces/channels
   - Groups have variation axes
   - Variants have attributes

## What Needs to Change

### Database Models
- `Product` → `Group` (or `ProductGroup`)
- `ProductVariantAxis` → `GroupVariantAxis`
- `ChannelVariantAxis.product` → `ChannelVariantAxis.group`
- `ChannelListing.product` → `ChannelListing.group`
- `Variant.product` → `Variant.group`
- `ProductAttributeValue.product` → `ProductAttributeValue.group` (or keep as is)

### API Endpoints
- `/api/v1/products/` → `/api/v1/groups/`
- `/api/v1/products/{id}/variants/` → `/api/v1/groups/{id}/variants/`
- `/api/v1/products/{id}/channel-axes/` → `/api/v1/groups/{id}/channel-axes/`

### Frontend
- "Products" page → "Groups" page
- "Product Detail" → "Group Detail"
- Clear distinction: Groups vs Variants

## Migration Strategy

1. **Option 1: Full Rename** (Recommended)
   - Create new models with new names
   - Migrate data
   - Update all code
   - Remove old models

2. **Option 2: Alias Approach**
   - Keep `Product` model but add `Group` as an alias
   - Update frontend to use "Group" terminology
   - Gradually migrate backend

3. **Option 3: Just Frontend Rename**
   - Keep backend as `Product`
   - Only change frontend labels to "Groups"
   - Less confusing but not ideal

## Recommendation

**Option 3 (Frontend-only rename)** is the quickest win:
- Change all UI labels from "Product" to "Group"
- Keep backend models as `Product` (less breaking changes)
- Add clear documentation explaining Product = Group
- Consider full rename later if needed

This gives immediate clarity without massive refactoring.
