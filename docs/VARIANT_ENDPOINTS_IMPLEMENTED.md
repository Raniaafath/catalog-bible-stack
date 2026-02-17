# Variant Management Endpoints - Implementation Summary

## ✅ Implemented Endpoints

All endpoints follow the **clean pattern**: variants are separate rows, product payloads stay clean (no nested writes).

### 1. List Variants for a Product
```
GET /api/v1/products/{id}/variants/
```
**Response**: Array of variant objects
```json
[
  {
    "id": 1,
    "product_id": 123,
    "sku": "ABC-RED-M",
    "barcode": "123456789",
    "mpn": "MPN-001",
    "internal_sku": "uuid-here",
    "axis_signature": "red:medium"
  }
]
```

### 2. Create Variant (Attached to Product)
```
POST /api/v1/products/{id}/variants/
Body: {
  "sku": "ABC-RED-M",
  "barcode": "123456789",
  "mpn": "MPN-001"
}
```
**Note**: `product_id` is automatically set from URL, not from payload.

**Response**: Created variant object (201 Created)

### 3. Group/Regroup Variants
```
POST /api/v1/products/{target_id}/group-variants/
Body: {
  "variant_ids": [1, 2, 3]
}
```
**Purpose**: Move multiple existing variants to a target product (grouping workflow)

**Response**:
```json
{
  "detail": "ok",
  "product_id": 123,
  "moved_variants": 3
}
```

**Validation**:
- Returns 400 if `variant_ids` is not a non-empty list
- Returns 400 if any variant IDs don't exist
- Uses `select_for_update()` for atomic transaction

### 4. Move Single Variant
```
POST /api/v1/variants/{id}/move-to-product/
Body: {
  "product_id": 123
}
```
**Purpose**: Move one variant to another product

**Response**: Updated variant object (200 OK)

**Validation**:
- Returns 400 if `product_id` is missing
- Returns 404 if target product doesn't exist

---

## Serializers

### `VariantSerializer` (Read/Update)
- **Read-only fields**: `id`, `product_id`, `internal_sku`, `axis_signature`
- **Writable fields**: `barcode`, `mpn`, `sku`
- **Note**: `product_id` is read-only because moves happen via dedicated actions

### `VariantCreateSerializer` (Create only)
- **Fields**: `sku`, `barcode`, `mpn`
- **No `product_id`**: Set automatically from URL in view

---

## Backend Rules Enforced

1. ✅ **Variants are separate rows** - No nested writes in Product payload
2. ✅ **Stable unique key** - `internal_sku` is auto-generated UUID (read-only)
3. ✅ **Atomic grouping** - `group_variants` uses `select_for_update()` transaction
4. ✅ **Clean separation** - Product updates don't touch variants, variant operations are explicit

---

## Usage in Frontend

### Add Variant to Product
```typescript
// In ProductDetail page
const addVariant = async (productId: number, data: { sku: string, barcode?: string }) => {
  const response = await fetch(`/api/v1/products/${productId}/variants/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  return response.json();
};
```

### Group Variants
```typescript
const groupVariants = async (targetProductId: number, variantIds: number[]) => {
  const response = await fetch(`/api/v1/products/${targetProductId}/group-variants/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ variant_ids: variantIds })
  });
  return response.json();
};
```

### Move Variant
```typescript
const moveVariant = async (variantId: number, targetProductId: number) => {
  const response = await fetch(`/api/v1/variants/${variantId}/move-to-product/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ product_id: targetProductId })
  });
  return response.json();
};
```

---

## Files Modified

1. **`api/v1/serializers/catalog.py`**
   - Added `VariantCreateSerializer`
   - Updated `VariantSerializer` to make `product_id` read-only

2. **`api/v1/views/catalog.py`**
   - Added `ProductViewSet.variants()` action (GET + POST)
   - Added `ProductViewSet.group_variants()` action (POST)
   - Added `VariantViewSet.move_to_product()` action (POST)

---

## Next Steps

1. ✅ **Backend endpoints** - DONE
2. ⏳ **Frontend UI** - Add "Add Variant" button in ProductDetail
3. ⏳ **Grouping UI** - Create UI for selecting variants and grouping them
4. ⏳ **Channel axes** - Add `ChannelVariantAxis` model and endpoints (separate task)
