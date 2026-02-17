# Channel-Specific Variation Axes

## Overview

**Problem**: Different marketplaces may need different variation axes for the same product family.

**Example**:
- **Shopify**: Uses `color` + `size` as axes
- **eBay**: Uses `color` + `size` + `material` as axes
- **Amazon**: Uses only `size` as axis

**Solution**: `ChannelVariantAxis` model stores marketplace-specific axes.

---

## Database Model

### `ChannelVariantAxis`

```python
class ChannelVariantAxis(models.Model):
    product = ForeignKey(Product)      # Product family/group
    channel = ForeignKey(Channel)      # Marketplace (shopify, ebay, etc.)
    attribute = ForeignKey(Attribute) # The axis attribute (color, size, etc.)
    position = IntegerField            # Order (0, 1, 2, ...)
    label_override = TextField         # Optional custom label
```

**Unique constraint**: `(product, channel, attribute)` - one axis per product+channel+attribute

**Indexes**:
- `(product, channel, position)` - for ordered queries
- `(channel)` - for channel-wide queries

---

## API Endpoints

### Get Axes for Product + Channel

```
GET /api/v1/products/{id}/channel-axes/?channel_id=1
```

**Response**:
```json
{
  "product_id": 123,
  "product_code": "BIKE-001",
  "channel": {
    "id": 1,
    "code": "shopify",
    "name": "Shopify"
  },
  "axes": [
    {
      "id": 10,
      "attribute": {
        "id": 5,
        "code": "color",
        "data_type": "enum"
      },
      "position": 0,
      "label_override": null
    },
    {
      "id": 11,
      "attribute": {
        "id": 6,
        "code": "size",
        "data_type": "enum"
      },
      "position": 1,
      "label_override": null
    }
  ]
}
```

### Set Axes for Product + Channel

```
POST /api/v1/products/{id}/channel-axes/
Body: {
  "channel_id": 1,
  "axes": [
    {"attribute_id": 5, "position": 0},  // color
    {"attribute_id": 6, "position": 1}   // size
  ]
}
```

**What happens**:
1. Deletes all existing axes for this product+channel
2. Creates new axes in the specified order

**Response**:
```json
{
  "detail": "ok",
  "product_id": 123,
  "channel_id": 1,
  "axes": [
    {"id": 10, "attribute_id": 5, "attribute_code": "color", "position": 0},
    {"id": 11, "attribute_id": 6, "attribute_code": "size", "position": 1}
  ]
}
```

### Delete Axes for Product + Channel

```
DELETE /api/v1/products/{id}/channel-axes/?channel_id=1
```

**Response**:
```json
{
  "detail": "ok",
  "deleted_count": 2
}
```

---

## Workflow

### Step 1: Import Products (Standalone)
- Import creates standalone products (no grouping, no axes)

### Step 2: Group Variants
- User groups variants into product families via UI
- `POST /api/v1/products/{id}/group-variants/`

### Step 3: Set Axes Per Marketplace
- For each marketplace, user selects which attributes are axes
- `POST /api/v1/products/{id}/channel-axes/` with `channel_id` and `axes`

**Example**:
```javascript
// Set axes for Shopify
POST /api/v1/products/123/channel-axes/
{
  "channel_id": 1,  // shopify
  "axes": [
    {"attribute_id": 5, "position": 0},  // color
    {"attribute_id": 6, "position": 1}   // size
  ]
}

// Set axes for eBay (different!)
POST /api/v1/products/123/channel-axes/
{
  "channel_id": 2,  // ebay
  "axes": [
    {"attribute_id": 5, "position": 0},  // color
    {"attribute_id": 6, "position": 1},  // size
    {"attribute_id": 7, "position": 2}   // material (extra!)
  ]
}
```

### Step 4: Generate Titles
- When generating titles for a specific locale + marketplace:
  1. Get axes for that product + channel: `GET /products/{id}/channel-axes/?channel_id=X`
  2. Use those axes to build variant-specific titles
  3. All variants in the group use the same template and keywords
  4. Only the axis values differ (e.g., "Red Medium" vs "Blue Large")

---

## Fallback Logic

If no `ChannelVariantAxis` exists for a product+channel:
- Fall back to `ProductVariantAxis` (global/default axes)
- If still none, use no axes (generate same title for all variants)

**Priority**:
1. `ChannelVariantAxis` (marketplace-specific) ← **Highest priority**
2. `ProductVariantAxis` (global/default) ← Fallback
3. No axes ← Last resort

---

## Example Use Case

### Product Family: "Mountain Bike Pro"
- **Variants**: Red-Small, Red-Large, Blue-Small, Blue-Large

### Shopify Configuration
```json
{
  "channel_id": 1,
  "axes": [
    {"attribute_id": 5, "position": 0},  // color
    {"attribute_id": 6, "position": 1}    // size
  ]
}
```

**Generated titles**:
- "Mountain Bike Pro - Red - Small"
- "Mountain Bike Pro - Red - Large"
- "Mountain Bike Pro - Blue - Small"
- "Mountain Bike Pro - Blue - Large"

### eBay Configuration
```json
{
  "channel_id": 2,
  "axes": [
    {"attribute_id": 6, "position": 0}    // size only
  ]
}
```

**Generated titles**:
- "Mountain Bike Pro - Small" (both Red and Blue variants)
- "Mountain Bike Pro - Large" (both Red and Blue variants)

**Note**: eBay doesn't show color in title, so variants are grouped by size only.

---

## Database Queries

### Get axes for product + channel
```python
from catalog.models import ChannelVariantAxis

axes = ChannelVariantAxis.objects.filter(
    product_id=123,
    channel_id=1
).select_related('attribute').order_by('position')
```

### Check if channel-specific axes exist
```python
has_channel_axes = ChannelVariantAxis.objects.filter(
    product_id=123,
    channel_id=1
).exists()

if has_channel_axes:
    # Use ChannelVariantAxis
    axes = ChannelVariantAxis.objects.filter(...)
else:
    # Fall back to ProductVariantAxis
    axes = ProductVariantAxis.objects.filter(product_id=123)
```

---

## Summary

✅ **Different axes per marketplace**: Same product can have different axes for Shopify vs eBay  
✅ **Stored in database**: `ChannelVariantAxis` table  
✅ **API endpoints**: Get/set/delete axes per product+channel  
✅ **Title generation**: Use axes when generating titles for specific locale+marketplace  
✅ **Fallback**: Uses `ProductVariantAxis` if no channel-specific axes defined
