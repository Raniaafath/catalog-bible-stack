# Listing Groups Explained

## What Are Listing Groups?

**Listing Groups** (called `ChannelListing` in the database) are marketplace-specific bundles of variants. They allow you to:

1. **Group variants differently per marketplace** - Same product can have different variant groupings on Amazon vs eBay vs Shopify
2. **Set different variation axes per listing** - Each listing group can have its own variation axes (color, size, etc.)
3. **Generate titles based on listing-specific axes** - Titles are generated using the axes defined for that specific listing group

## Real-World Example

Imagine you have a product "Mountain Bike Pro" with variants:
- Red, Small
- Red, Medium  
- Red, Large
- Blue, Small
- Blue, Medium
- Blue, Large

**On Amazon:**
- Listing Group 1: All variants together with axes `[color, size]`
  - Title: "Mountain Bike Pro - Red Small"
  - Title: "Mountain Bike Pro - Blue Large"
  - etc.

**On eBay:**
- Listing Group 1: Red variants only with axis `[size]`
  - Title: "Mountain Bike Pro - Small"
  - Title: "Mountain Bike Pro - Medium"
- Listing Group 2: Blue variants only with axis `[size]`
  - Title: "Mountain Bike Pro - Small"
  - Title: "Mountain Bike Pro - Medium"

This allows you to optimize listings per marketplace's requirements!

---

## Database Structure

### 1. `ChannelListing` (Listing Group)

**Table:** `pub_channellisting`

**Purpose:** Represents one listing on a marketplace for a product.

**Fields:**
```python
- id: Primary key
- product: ForeignKey to Product (which product this listing is for)
- channel: ForeignKey to Channel (Amazon, eBay, Shopify, etc.)
- locale: ForeignKey to Locale (optional - for locale-specific listings)
- name: CharField (optional label like "eBay - Red variants only")
- is_default: BooleanField (only one default per product+channel+locale)
- created_at, updated_at: Timestamps
```

**Constraints:**
- Only ONE default listing per `(product, channel, locale)` combination
- Multiple non-default listings allowed

**Example Data:**
```
id | product_id | channel_id | locale_id | name                    | is_default
---|------------|------------|-----------|-------------------------|------------
1  | 560        | 1          | NULL      | "eBay - Red variants"   | True
2  | 560        | 1          | NULL      | "eBay - Blue variants"  | False
3  | 560        | 2          | NULL      | NULL                    | True
```

---

### 2. `ChannelListingAxis` (Axes per Listing)

**Table:** `catalog_channellistingaxis`

**Purpose:** Defines which attributes are variation axes for THIS specific listing group.

**Fields:**
```python
- id: Primary key
- listing: ForeignKey to ChannelListing (which listing this axis belongs to)
- attribute: ForeignKey to Attribute (the axis attribute: color, size, etc.)
- position: IntegerField (order: 0 = first axis, 1 = second axis, etc.)
- label_override: TextField (optional custom label for this axis)
- enabled: BooleanField (whether this axis is active)
- created_at: Timestamp
```

**Example Data:**
```
id | listing_id | attribute_id | position | label_override | enabled
---|------------|--------------|----------|-----------------|--------
1  | 1          | 157          | 0        | "Color"         | True
2  | 1          | 158          | 1        | NULL            | True
3  | 2          | 158          | 0        | "Size"          | True
```

This means:
- Listing 1 uses axes: `[color (pos 0), size (pos 1)]`
- Listing 2 uses axes: `[size (pos 0)]`

---

### 3. `ChannelListingMap` (Variant → Listing Mapping)

**Table:** `pub_channellistingmap`

**Purpose:** Maps which variants belong to which listing group.

**Fields:**
```python
- id: Primary key
- listing: ForeignKey to ChannelListing (which listing group, nullable)
- variant: ForeignKey to Variant (which variant)
- channel: ForeignKey to Channel (which marketplace)
- external_id: CharField (marketplace's ID for this variant)
- last_sync_at: DateTimeField (when last synced to marketplace)
- sync_status: CharField (sync status)
- error_json: JSONField (sync errors)
```

**Key Rule:** A variant can only belong to ONE listing per channel.

**Example Data:**
```
id | listing_id | variant_id | channel_id | external_id
---|------------|------------|------------|------------
1  | 1          | 557        | 1          | "EBAY-12345"
2  | 1          | 558        | 1          | "EBAY-12346"
3  | 2          | 559        | 1          | "EBAY-12347"
4  | NULL       | 560        | 2          | "AMZ-78901"
```

This means:
- Variants 557, 558 belong to Listing 1 (eBay - Red variants)
- Variant 559 belongs to Listing 2 (eBay - Blue variants)
- Variant 560 is on Amazon but not in a specific listing group (uses default)

---

## How Title Generation Works

### Axis Resolution Priority (Planned)

When generating a title for a variant on a marketplace, the system **should** resolve axes in this order:

1. **`ChannelListingAxis`** (listing-specific) ← **Highest Priority** ⚠️ *Not yet implemented*
   - If variant belongs to a listing group, use that listing's axes
   
2. **`ChannelVariantAxis`** (product+channel) ← Fallback ⚠️ *Not yet implemented*
   - If no listing-specific axes, use product+channel axes
   
3. **`ProductVariantAxis`** (global/default) ← **Currently Used**
   - Currently, title generation uses global product axes only

**Note:** The title renderer (`pub/services/title_renderer.py`) currently only uses `ProductVariantAxis`. To fully support listing groups, it needs to be updated to:
1. Check if variant belongs to a `ChannelListing` 
2. Use `ChannelListingAxis` if available
3. Fall back to `ChannelVariantAxis` if no listing axes
4. Fall back to `ProductVariantAxis` as last resort

### Title Generation Flow

```
1. User requests title for: Variant 557 on eBay (channel_id=1)
   ↓
2. System finds: ChannelListingMap(variant=557, channel=1)
   → listing_id = 1
   ↓
3. System gets axes: ChannelListingAxis.objects.filter(listing_id=1)
   → axes = [color (pos 0), size (pos 1)]
   ↓
4. System gets variant's attribute values:
   → color = "Red"
   → size = "Medium"
   ↓
5. System generates title using template:
   → "Mountain Bike Pro - Red Medium"
```

### Example: Different Titles for Same Variant

**Variant:** Red Medium Bike (variant_id=557)

**On eBay (Listing Group 1 - axes: [color, size]):**
- Title: "Mountain Bike Pro - Red Medium"

**On Amazon (Listing Group 2 - axes: [size]):**
- Title: "Mountain Bike Pro - Medium"

**On Shopify (no listing group, uses ChannelVariantAxis - axes: [color]):**
- Title: "Mountain Bike Pro - Red"

---

## Database Relationships Diagram

```
Product (id: 560, code: "bike-pro")
│
├── Variant (id: 557, sku: "BIKE-001-R-M")
├── Variant (id: 558, sku: "BIKE-001-R-L")
└── Variant (id: 559, sku: "BIKE-001-B-M")
    │
    └── ProductAttributeValue (variant=557, attribute=color, value="Red")
    └── ProductAttributeValue (variant=557, attribute=size, value="Medium")
    │
    └── ChannelListingMap (variant=557, channel=eBay, listing=1)
    └── ChannelListingMap (variant=558, channel=eBay, listing=1)
    └── ChannelListingMap (variant=559, channel=eBay, listing=2)

ChannelListing (id: 1, product=560, channel=eBay, name="Red variants")
│
├── ChannelListingAxis (listing=1, attribute=color, position=0)
├── ChannelListingAxis (listing=1, attribute=size, position=1)
│
└── ChannelListingMap (listing=1, variant=557)
└── ChannelListingMap (listing=1, variant=558)

ChannelListing (id: 2, product=560, channel=eBay, name="Blue variants")
│
├── ChannelListingAxis (listing=2, attribute=size, position=0)
│
└── ChannelListingMap (listing=2, variant=559)
```

---

## API Endpoints

### Create Listing Group
```
POST /api/v1/channel-listings/
{
  "product_id": 560,
  "channel_id": 1,
  "locale_id": null,
  "name": "eBay - Red variants",
  "is_default": true
}
```

### Add Variants to Listing
```
POST /api/v1/channel-listings/{id}/add-variants/
{
  "variant_ids": [557, 558]
}
```

### Set Listing Axes
```
POST /api/v1/channel-listings/{id}/axes/
{
  "axes": [
    {"attribute_id": 157, "position": 0, "label_override": "Color"},
    {"attribute_id": 158, "position": 1}
  ]
}
```

### Generate Titles for Listing
```
POST /api/v1/translations/generate/
{
  "listing_id": 1,
  "locale_id": 1,
  "channel_id": 1
}
```

---

## Summary

**Listing Groups (`ChannelListing`)** allow you to:
1. ✅ Group variants differently per marketplace
2. ✅ Set different variation axes per listing
3. ✅ Generate marketplace-specific titles based on listing axes

**Database Tables:**
- `pub_channellisting` - The listing groups
- `catalog_channellistingaxis` - Axes per listing
- `pub_channellistingmap` - Variant → Listing mapping

**Title Generation:**
- Uses listing-specific axes (highest priority)
- Falls back to product+channel axes if no listing axes
- Falls back to global axes as last resort

This gives you full control over how variants are presented on each marketplace! 🎯
