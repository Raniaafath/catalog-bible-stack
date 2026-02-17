# Catalog Architecture: Canonical Catalog + Publishing Layer

## Overview

This document describes the architecture decision for managing product catalogs across multiple marketplaces. This follows industry-standard patterns used by PIMs (Product Information Management systems), Shopify, Amazon, and other marketplace platforms.

---

## The Problem

Different marketplaces have different requirements:

- **Different variation axes**: Shopify might use `color + size`, while eBay uses `color` only, and Amazon uses `size + pack_count` (depending on category)
- **Different grouping strategies**: One marketplace might require one listing with all variants, while another needs multiple listings split by color
- **Different content**: Titles, descriptions, keywords, and templates vary by marketplace and locale
- **Different variant inclusion**: Some marketplaces only publish in-stock sizes, or exclude certain colors

The challenge: **How do you maintain one canonical catalog while supporting all these marketplace-specific requirements?**

---

## Industry Standard Pattern

### 1. Canonical Catalog (Independent of Marketplaces)

**One source of truth** that doesn't change based on marketplace requirements:

- **Product** (family/SPU/parent/product model)
  - Shared attributes: brand, model, series, material, etc.
  - Product-level specifications
  
- **Variant** (SKU/child)
  - Variant-specific attributes: color, size, pack_count, etc.
  - Variant-level values stored in `ProductAttributeValue`

**This is your stable, marketplace-independent catalog.** It should never be modified to match a specific marketplace.

### 2. Publishing Layer (Per Channel)

**Configuration and content** that varies by marketplace:

- **Variant inclusion**: Which SKUs are published on which channel
- **Variation axes**: Which attributes are used as axes on each channel
- **Content**: Titles, descriptions, keywords, templates (vary by channel + locale)
- **Listing groups**: Multiple listings per product+channel when needed

This layer **references** the canonical catalog but doesn't duplicate it.

---

## Our Implementation

### Canonical Catalog Layer

#### `Product` (Family/SPU)
```python
class Product(models.Model):
    code = CharField(unique=True)  # "BIKE-001"
    product_type = ForeignKey(ProductType)
    brand = CharField()
    model = CharField()
    # ... shared attributes
```

#### `Variant` (SKU)
```python
class Variant(models.Model):
    product = ForeignKey(Product)  # Links to family
    sku = CharField(unique=True)  # "BIKE-001-RED-M"
    axis_signature = CharField()  # "red:medium"
    # ... variant-specific attributes
```

#### `ProductAttributeValue`
Stores attribute values at product or variant level:
- Product-level: brand, model, material (shared across variants)
- Variant-level: color, size, pack_count (differs per variant)

---

### Publishing Layer (Basic)

For simple cases where you have **≤ 1 listing per (product, channel)**:

#### `ChannelListingMap` (Variant Inclusion)
```python
class ChannelListingMap(models.Model):
    variant = ForeignKey(Variant)
    channel = ForeignKey(Channel)
    listing = ForeignKey(ChannelListing, null=True)  # Optional listing group
    external_id = CharField()  # External marketplace ID
    sync_status = CharField()
    # ... sync metadata
```

**Purpose**: Maps which variants are published on which channels.

#### `ChannelVariantAxis` (Axes per Product+Channel)
```python
class ChannelVariantAxis(models.Model):
    product = ForeignKey(Product)
    channel = ForeignKey(Channel)
    attribute = ForeignKey(Attribute)  # The axis (color, size, etc.)
    position = IntegerField()
    label_override = TextField()
```

**Purpose**: Defines which attributes are variation axes for this product on this channel.

**Example**:
- Product "BIKE-001" on Shopify: axes = `[color, size]`
- Product "BIKE-001" on eBay: axes = `[color]`
- Product "BIKE-001" on Amazon: axes = `[size, pack_count]`

---

### Publishing Layer (Advanced: Listing Groups)

For cases where you need **> 1 listing per (product, channel)**:

#### `ChannelListing` (Listing Group)
```python
class ChannelListing(models.Model):
    product = ForeignKey(Product)
    channel = ForeignKey(Channel)
    locale = ForeignKey(Locale, null=True)  # Optional locale-specific
    name = CharField()  # "eBay – Red variants only"
    is_default = BooleanField()  # Default listing for product+channel+locale
```

**Purpose**: Represents one listing on a marketplace. Allows multiple listings per product+channel.

**Constraints**: 
- Only one default listing per `(product, channel, locale)`
- Multiple non-default listings allowed

#### `ChannelListingAxis` (Axes per Listing)
```python
class ChannelListingAxis(models.Model):
    listing = ForeignKey(ChannelListing)
    attribute = ForeignKey(Attribute)
    position = IntegerField()
    label_override = TextField()
    enabled = BooleanField()
```

**Purpose**: Defines axes for a specific listing group. Allows different axes per listing.

**Example**:
- Product "BIKE-001" on eBay:
  - Listing 1 (Red variants): axes = `[size]`
  - Listing 2 (Blue variants): axes = `[size]`
  - Both use different axes than the default `ChannelVariantAxis`

#### `ChannelListingMap.listing`
The `ChannelListingMap` model has an optional `listing` field that links variants to specific listing groups.

---

## Decision Rule

### When to Use What

**Simple case (≤ 1 listing per product+channel):**
- Use `ChannelVariantAxis(product, channel)`
- Store axes at the product+channel level
- All variants in the product use the same axes for that channel

**Complex case (> 1 listing per product+channel):**
- Create `ChannelListing` groups (one per listing)
- Use `ChannelListingAxis(listing)` for axes per listing
- Link variants to listings via `ChannelListingMap.listing`
- Fallback to `ChannelVariantAxis` if no listing-specific axes exist

---

## Resolution Priority (For Title Generation)

When generating titles or determining axes, use this priority:

1. **`ChannelListingAxis`** (listing-specific) ← **Highest priority**
   - Use if the variant has a `listing` and that listing has axes defined
   
2. **`ChannelVariantAxis`** (product+channel) ← **Fallback**
   - Use if no listing-specific axes, but product+channel axes exist
   
3. **`ProductVariantAxis`** (global/default) ← **Last resort**
   - Use if no channel-specific axes exist

This ensures:
- Listing-specific configuration overrides channel defaults
- Channel-specific configuration overrides global defaults
- System always has a fallback

---

## Examples

### Example 1: Simple Case (One Listing per Marketplace)

**Product**: "Mountain Bike Pro"
**Variants**: Red-Small, Red-Large, Blue-Small, Blue-Large

**Shopify Configuration**:
```python
ChannelVariantAxis(product="BIKE-001", channel="shopify", attribute="color", position=0)
ChannelVariantAxis(product="BIKE-001", channel="shopify", attribute="size", position=1)
```
→ One listing with all variants, axes: `color + size`

**eBay Configuration**:
```python
ChannelVariantAxis(product="BIKE-001", channel="ebay", attribute="color", position=0)
```
→ One listing with all variants, axes: `color` only

**Result**: Generated titles differ per marketplace but use the same canonical product/variant data.

---

### Example 2: Complex Case (Multiple Listings per Marketplace)

**Product**: "Mountain Bike Pro"
**Variants**: Red-Small, Red-Large, Blue-Small, Blue-Large

**eBay Configuration** (split by color):

**Listing 1: Red Variants**
```python
listing1 = ChannelListing(product="BIKE-001", channel="ebay", name="Red variants", is_default=False)
ChannelListingAxis(listing=listing1, attribute="size", position=0)
ChannelListingMap(variant="BIKE-001-RED-S", listing=listing1)
ChannelListingMap(variant="BIKE-001-RED-L", listing=listing1)
```

**Listing 2: Blue Variants**
```python
listing2 = ChannelListing(product="BIKE-001", channel="ebay", name="Blue variants", is_default=False)
ChannelListingAxis(listing=listing2, attribute="size", position=0)
ChannelListingMap(variant="BIKE-001-BLUE-S", listing=listing2)
ChannelListingMap(variant="BIKE-001-BLUE-L", listing=listing2)
```

**Result**: Two separate eBay listings, each with different variants and potentially different axes.

---

## Evolution Path

This architecture follows a common evolution path:

### Phase 1: Simple (Current)
- Canonical catalog: `Product` + `Variant`
- Basic publishing: `ChannelListingMap` + `ChannelVariantAxis`
- Works for 90% of use cases (one listing per product+channel)

### Phase 2: Advanced (Just Implemented)
- Add listing groups: `ChannelListing` + `ChannelListingAxis`
- Support multiple listings per product+channel
- Maintain backward compatibility (all existing code continues to work)

**Migration Strategy**:
- Existing `ChannelVariantAxis` records remain valid
- Existing `ChannelListingMap` records work without listing groups
- Default listings created automatically via data migration
- System falls back to `ChannelVariantAxis` when no listing-specific axes exist

---

## Why This Pattern?

### Benefits

1. **Single Source of Truth**: Product and variant data never duplicated or modified per marketplace
2. **Flexibility**: Support different axes, grouping strategies, and content per marketplace
3. **Scalability**: Easy to add new marketplaces without touching canonical catalog
4. **Maintainability**: Changes to product specs update all marketplaces automatically
5. **Industry Alignment**: Follows patterns used by Shopify, Amazon, PIMs

### Common Alternatives (Why We Don't Use Them)

**❌ Duplicate catalog per marketplace**:
- Problem: Same product stored 5 times for 5 marketplaces
- Result: Data divergence, maintenance nightmare

**❌ Modify canonical catalog per marketplace**:
- Problem: Base catalog becomes polluted with marketplace-specific logic
- Result: Cannot add new marketplaces without breaking existing ones

**✅ Our approach: Canonical + Publishing Layer**:
- Canonical catalog stays stable
- Publishing layer handles all marketplace differences
- Best of both worlds

---

## Database Schema

```
Canonical Catalog:
├── Product (family)
│   └── Variant (SKU)
│       └── ProductAttributeValue (attribute values)

Publishing Layer (Basic):
├── ChannelListingMap (variant → channel mapping)
└── ChannelVariantAxis (axes per product+channel)

Publishing Layer (Advanced):
├── ChannelListing (listing group)
│   ├── ChannelListingAxis (axes per listing)
│   └── ChannelListingMap.listing (variant → listing)
└── ChannelVariantAxis (fallback axes)
```

---

## Summary

This architecture implements the **industry-standard pattern** of separating canonical catalog from publishing configuration:

1. **Canonical catalog** = stable, marketplace-independent (`Product` + `Variant`)
2. **Publishing layer** = marketplace-specific configuration (`ChannelListingMap`, `ChannelVariantAxis`, `ChannelListing`, `ChannelListingAxis`)

**Evolution path**: Start simple with product+channel axes, add listing groups when needed.

**Decision rule**: Use `ChannelVariantAxis` for ≤ 1 listing per product+channel, use `ChannelListing` + `ChannelListingAxis` for > 1 listing.

**Resolution priority**: Listing axes → Channel axes → Global axes (with fallbacks at each level).

This ensures your catalog remains clean, flexible, and aligned with how modern marketplace systems work.
