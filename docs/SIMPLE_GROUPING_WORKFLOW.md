# Simple Product Grouping Workflow

## Overview

This document describes the **simple, user-controlled workflow** for importing and grouping product variants:

1. User chooses a product category
2. User imports a CSV or Excel file
3. Rows become **variants** (each with an SKU)
4. Attributes are mapped and **upserted** (create new attributes if needed)
5. **Products are just containers** for grouping variants
6. **Grouping happens manually** when the user decides

---

## Step-by-Step Workflow

### Step 1: Choose Product Category

**Frontend:** `/imports/new`

User selects a product category (ProductType) from a dropdown. This category will be applied to all imported variants.

**API:** The category is assigned during the import process via the category assignment step.

---

### Step 2: Import CSV/Excel File

**Frontend:** `/imports/new`

User uploads a CSV or Excel file. Each row in the file will become a **variant**.

**Key Setting:**
- `group_by_product_key: false` (default) → Each variant gets its own standalone product initially
- This allows manual grouping later

**What Happens:**
- File is parsed and columns are detected
- Each row creates a **Variant** with:
  - SKU (from VARIANT_KEY column or auto-generated)
  - A placeholder **Product** (one per variant)
  - Status: DRAFT

---

### Step 3: Map Attributes

**Frontend:** `/imports/{id}/map-attributes`

User maps CSV columns to attributes:

- **Map to existing attribute**: Select from dropdown
- **Create new attribute**: System creates it automatically
- **Standard fields**: SKU, Title, Description, etc.

**What Happens:**
- Attributes are **upserted** (created if they don't exist)
- Attribute values are linked to variants via `ProductAttributeValue`
- Each variant stores its own attribute values

**Example:**
```
CSV Column    →  Attribute        →  Action
--------------------------------------------------
SKU           →  VARIANT_KEY      →  System field
Color         →  color (enum)     →  Upsert values: Red, Blue, Green
Size          →  size (enum)      →  Upsert values: S, M, L, XL
Material      →  material (text)  →  Create if new
Price         →  price (number)   →  Create if new
```

---

### Step 4: Process Import

**Frontend:** `/imports/{id}/preview` → Click "Process Import"

**What Happens:**
- Variants are created/updated (upserted by SKU)
- Each variant gets its own **Product** (standalone mode)
- Attribute values are stored and linked to variants
- Products are created with status: DRAFT

**Result:**
- Each CSV row = 1 Variant = 1 Product (initially)
- Variants are ready for manual grouping

---

### Step 5: Manual Grouping (When User Decides)

**Frontend:** `/products/variants`

#### 5.1: User Selects Variants

User selects multiple variants (e.g., 5 variants) that should be grouped together.

#### 5.2: User Chooses Marketplace

User selects a marketplace/channel (e.g., Shopify, Amazon, etc.).

**Why marketplace?**
- Different marketplaces can have different variation axes
- Axes are stored per channel via `ChannelVariantAxis`

#### 5.3: User Clicks "Group Now"

**Frontend:** Opens `GroupingDialog`

**What Happens:**
1. System calls `POST /api/v1/variants/compare/` with selected variant IDs
2. System detects which attributes differ between the selected variants
3. System shows differences to the user

**Example Differences:**
```
Selected Variants: BIKE-001-RED-M, BIKE-001-RED-L, BIKE-001-BLUE-M, BIKE-001-BLUE-L

Differences Detected:
- color: Red, Blue (2 values) ✅ Recommended axis
- size: Medium, Large (2 values) ✅ Recommended axis
- price: 599.99, 649.99 (2 values) ⚠️ Not recommended (too many values)

Common Attributes:
- brand: Trek (same for all)
- material: Aluminum (same for all)
```

#### 5.4: User Selects Variation Axes

User selects one or more differences to define as **variation axes** (axes de variation).

**What are variation axes?**
- Attributes that differentiate variants within a product family
- Examples: color, size, capacity, material
- Used for generating variant-specific titles

**User Action:**
- Checkboxes for each difference
- System recommends axes with 2-10 unique values
- User can select/deselect any difference

**Example Selection:**
```
✅ color (2 values: Red, Blue)
✅ size (2 values: Medium, Large)
☐ price (2 values: 599.99, 649.99)  ← User doesn't select this
```

#### 5.5: User Saves

**API Call:**
```bash
POST /api/v1/variants/group-with-axes/
{
  "variant_ids": [1, 2, 3, 4, 5],
  "channel_id": 5,  // Shopify
  "variation_axes": [
    {"attribute_id": 10, "position": 0},  // color
    {"attribute_id": 11, "position": 1}    // size
  ],
  "create_new_product": true,
  "product_code": "mountain-bike-pro"
}
```

**What Happens:**
1. System creates a new **Product** (or uses existing)
2. System moves all selected variants to this product
3. System creates **ChannelVariantAxis** records for the selected axes
4. Variants are now grouped under one product

**Result:**
- 5 variants → 1 Product
- Variation axes stored per channel
- Ready for title generation

---

## Database Structure

### Products
```sql
catalog_product
  id | code              | product_type_id | status
  1  | mountain-bike-pro | 5               | DRAFT
```

**Purpose:** Container for grouping variants. No product-level data required.

### Variants
```sql
catalog_variant
  id | product_id | sku              | barcode
  1  | 1          | BIKE-001-RED-M   | 1234567890
  2  | 1          | BIKE-001-RED-L   | 1234567891
  3  | 1          | BIKE-001-BLUE-M  | 1234567892
  4  | 1          | BIKE-001-BLUE-L  | 1234567893
```

**Key:** Each variant has an SKU. Variants are linked to products via `product_id` FK.

### Attributes & Values
```sql
catalog_attribute
  id | code  | data_type
  10 | color | ENUM
  11 | size  | ENUM

catalog_attributevalue
  id | attribute_id | code
  50 | 10           | red
  51 | 10           | blue
  60 | 11           | medium
  61 | 11           | large

catalog_productattributevalue
  id | variant_id | attribute_id | attribute_value_id
  1  | 1          | 10           | 50  (red)
  2  | 1          | 11           | 60  (medium)
  3  | 2          | 10           | 50  (red)
  4  | 2          | 11           | 61  (large)
```

**Key:** Attributes are created/upserted during import. Values are linked to variants.

### Variation Axes (Channel-Specific)
```sql
pub_channelvariantaxis
  id | product_id | channel_id | attribute_id | position
  1  | 1          | 5          | 10           | 0  (color)
  2  | 1          | 5          | 11           | 1  (size)
```

**Key:** Axes are stored per channel. Different marketplaces can have different axes.

---

## Key Principles

1. **Variants First**: Each CSV row = 1 Variant (with SKU)
2. **Products are Containers**: Products only exist to group variants
3. **Attributes are Upserted**: Create new attributes if they don't exist
4. **Manual Grouping**: User decides when and how to group variants
5. **Channel-Specific Axes**: Different marketplaces can have different variation axes
6. **Difference Detection**: System shows what differs between selected variants
7. **User Control**: User selects which differences become variation axes

---

## API Endpoints

### Import
- `POST /api/v1/imports/` - Upload file (with `group_by_product_key: false`)
- `POST /api/v1/imports/{id}/assign-category/` - Assign category
- `POST /api/v1/imports/{id}/map-attributes/` - Map columns to attributes
- `POST /api/v1/imports/{id}/process/` - Process import (create variants)

### Grouping
- `POST /api/v1/variants/compare/` - Compare variants and detect differences
- `POST /api/v1/variants/group-with-axes/` - Group variants with selected axes

---

## Example: Complete Flow

### 1. Import File
```csv
SKU,Color,Size,Price
BIKE-001-RED-M,Red,Medium,599.99
BIKE-001-RED-L,Red,Large,649.99
BIKE-001-BLUE-M,Blue,Medium,599.99
BIKE-001-BLUE-L,Blue,Large,649.99
```

### 2. Map Attributes
- `SKU` → VARIANT_KEY
- `Color` → color (enum) - Create new
- `Size` → size (enum) - Create new
- `Price` → price (number) - Create new

### 3. Process Import
**Result:**
- 4 Variants created (each with its own Product)
- Attributes created: color, size, price
- Values linked to variants

### 4. User Groups Variants
**User Action:**
1. Selects all 4 variants
2. Chooses "Shopify" marketplace
3. Clicks "Group Now"
4. System shows differences:
   - color: Red, Blue ✅
   - size: Medium, Large ✅
   - price: 599.99, 649.99 ⚠️
5. User selects: color, size
6. User saves

**Result:**
- 4 variants → 1 Product ("mountain-bike-pro")
- Variation axes: color (position 0), size (position 1)
- Stored for Shopify channel

---

## Summary

**Import Flow:**
1. Choose category
2. Upload CSV/Excel
3. Map attributes (upsert)
4. Process → Creates variants (standalone products)

**Grouping Flow:**
1. Select variants
2. Choose marketplace
3. Click "Group Now"
4. System shows differences
5. User selects variation axes
6. Save → Variants grouped under one product

**Key:** Products are just containers. Grouping is manual and user-controlled.
