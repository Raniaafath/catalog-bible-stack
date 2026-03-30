# Listing Group Workflow

A listing group (`ChannelListing`) is a marketplace-specific bundle of variants with its own variation axes and generated titles. You can have multiple listing groups per product+channel (e.g. red-only vs blue-only on eBay).

---

## Full workflow

```
1. Create listing group         POST /channel-listings/
2. Add variants                 POST /channel-listings/{id}/move-variants/
3. Set variation axes           POST /channel-listings/{id}/axes/
4. Create title template        POST /channel-listings/{id}/create-default-template/
5. Generate titles              POST /channel-listings/{id}/generate-titles/
6. Review generated titles      GET  /channel-listings/{id}/generated-titles/
```

All steps are ✅ implemented and working.

---

## Step by step

### 1. Create listing group
**UI:** `/groups` → "New Listing Group"
**API:** `POST /api/v1/channel-listings/`

Select: product, channel, optional name. Creates an empty listing group.

---

### 2. Add variants
**UI:** `/groups/{id}` → Variants tab → "Add Variants"
**API:** `POST /api/v1/channel-listings/{id}/move-variants/`

Picks variants from the same product. A variant can only belong to one listing per channel — adding it here removes it from any other listing on the same channel.

---

### 3. Set variation axes
**UI:** `/groups/{id}` → Variation Axes tab
**API:** `GET/POST /api/v1/channel-listings/{id}/axes/`

The system shows which attributes differ between variants (auto-detected). Check/uncheck to enable/disable axes, drag to reorder. Axes are stored in `ChannelListingAxis` and take highest priority in title rendering (above channel-level and product-level axes).

---

### 4. Create title template
**UI:** `/groups/{id}` → click "Create default template"
**API:** `POST /api/v1/channel-listings/{id}/create-default-template/`

Creates a `Template` scoped to this product type + channel + locale with the structure:
`[Head term] - [Hook term]`

You can extend it with attribute parts via the Template Wizard (`/templates/new`).

---

### 5. Generate titles
**UI:** `/groups/{id}` → "Generate Titles" button, choose locale
**API:** `POST /api/v1/channel-listings/{id}/generate-titles/`

```json
{ "locale_code": "fr-FR", "template_id": 7 }
```

Generates one title per variant using the template. If no `template_id` is given, the latest active template for this product type + channel + locale is used. Titles are stored in `GenerationOutput`.

---

### 6. Review generated titles
**UI:** `/groups/{id}` → Generated Titles tab
**API:** `GET /api/v1/channel-listings/{id}/generated-titles/`
**Edit single:** `PATCH /api/v1/channel-listings/{id}/generated-titles/{variant_id}/`

---

## Axis resolution priority (during title generation)

```
1. ChannelListingAxis  (this listing)          ← highest
2. ChannelVariantAxis  (product + channel)
3. ProductVariantAxis  (product default)       ← lowest
```

Code entry point: `catalog.services.axis_resolution.get_axes_for_context()`

---

## Database tables

| Table | Role |
|-------|------|
| `pub_channellisting` | The listing group |
| `pub_channellistingmap` | Variant → listing mapping |
| `catalog_channellistingaxis` | Axes per listing (position, label override) |
| `pub_template` | Title template scoped to product type + channel + locale |
| `pub_generationoutput` | Generated titles per variant |
