# Grouping and Marketplace Axes

This document defines the **two levels of grouping** (catalog vs marketplace) and how **variation axes** are resolved. It is the single reference for "product family", "listing group", and axis priority.

---

## Two Levels of Grouping

| Level | Concept | Model | Role |
|-------|--------|--------|------|
| **Catalog (canonical)** | **Product family** | `Product` | Groups variants in the single canonical catalog. Each variant belongs to exactly one Product. Independent of channels. |
| **Marketplace** | **Listing group** | `ChannelListing` (in `pub`) | For a (Product, Channel, optional Locale), defines **which variants** are published together and **which variation axes** apply to this listing. Multiple listing groups per product+channel = different variant sets and/or axes per marketplace. |

### Intent

On each marketplace you can have:

- **Different variant groups**: e.g. on eBay one listing group "Red variants only", another "Blue variants only".
- **Different variation axes per listing**: e.g. Listing 1 uses axis [size] only; Listing 2 uses [color, size].
- **Different axes per channel**: e.g. Shopify uses [color, size], Amazon uses [size] only.

So: **groupings of variants** and **axes of variation** are both configurable per marketplace and per listing group.

---

## Layer Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  CATALOG (canonical)                                             │
│  - Product (product family)                                      │
│  - Variant (SKU)                                                 │
│  - Attribute, ProductAttributeValue                              │
│  - ProductVariantAxis (default axes for the product)              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ referenced by
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  MARKETPLACE / PUB                                               │
│  - Channel (e.g. Shopify, eBay)                                   │
│  - ChannelListing (listing group = variant set + axes)            │
│  - ChannelListingMap (variant → listing group)                    │
│  - ChannelVariantAxis (axes per product + channel)               │
│  - ChannelListingAxis (axes per listing group)                    │
└─────────────────────────────────────────────────────────────────┘
```

**Axis resolution** (single place in code: `catalog.services.axis_resolution.get_axes_for_context`):

1. **ChannelListingAxis** (listing-specific) ← highest priority  
2. **ChannelVariantAxis** (product + channel) ← fallback  
3. **ProductVariantAxis** (product default) ← last resort  

---

## Product Family (Product)

- **What it is**: The catalog-level container for variants. One product family has many variants.
- **Where**: `catalog.Product`
- **Use**: Import and grouping assign variants to a product; product-level attributes and default axes (ProductVariantAxis) are defined here. No notion of channel or marketplace.

---

## Listing Group (ChannelListing)

- **What it is**: A marketplace-specific set of variants plus the axes used for that set (titles, filters, presentation).
- **Where**: `pub.ChannelListing`, `pub.ChannelListingMap`
- **Use**: For a given (Product, Channel, optional Locale), you can create multiple listing groups. Each group has:
  - A set of variants (via ChannelListingMap)
  - Optionally its own variation axes (ChannelListingAxis); otherwise channel axes (ChannelVariantAxis) or product axes (ProductVariantAxis) apply.

---

## Variation Axes (Three Levels)

| Level | Model | Scope | When used |
|-------|--------|--------|-----------|
| Listing | `ChannelListingAxis` | One listing group | When generating titles or presenting variants for that listing. |
| Channel | `ChannelVariantAxis` | Product + Channel | When no listing-specific axes are set. |
| Product | `ProductVariantAxis` | Product | When no channel or listing axes are set (catalog default). |

All three store: `attribute`, `position`, `label_override`. ChannelListingAxis also has `enabled`.

---

## Code Entry Point

Use a single service for resolving axes so priority and ordering are defined in one place:

- **Module**: `catalog.services.axis_resolution`
- **Function**: `get_axes_for_context(product, channel=None, listing=None)`
  - If `listing` is provided and has ChannelListingAxis (enabled): return those, ordered by position.
  - Else if `channel` is provided and the product has ChannelVariantAxis for that channel: return those.
  - Else: return ProductVariantAxis for the product.

Title generation and listing APIs should call this instead of querying axes directly.

---

## See Also

- [CATALOG_ARCHITECTURE.md](CATALOG_ARCHITECTURE.md) – Catalog layer detail  
- [CHANNEL_VARIANT_AXES.md](CHANNEL_VARIANT_AXES.md) – Channel-level axes API  
- [LISTING_GROUPS_EXPLAINED.md](LISTING_GROUPS_EXPLAINED.md) – Listing groups and ChannelListing
