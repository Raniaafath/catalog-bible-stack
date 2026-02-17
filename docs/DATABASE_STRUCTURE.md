# Database Structure: Product vs Variant

## ✅ Yes, there IS a Variant table

**Table name**: `catalog_variant`

## Database Relationship

### Product = PARENT (Family/Group)
- **Table**: `catalog_product`
- **Represents**: The product family/group
- **Fields**: `code`, `brand`, `model`, `product_type_id`, `status`, etc.

### Variant = CHILD (Individual SKU)
- **Table**: `catalog_variant`
- **Represents**: Individual sellable item/SKU
- **Fields**: `sku`, `barcode`, `mpn`, `product_id` (FK), `axis_signature`

## Relationship Direction

```
Product (PARENT)
  ├─ id: 301
  ├─ code: "BIKE-001"
  ├─ brand: "Trek"
  └─ variants (related_name) ← One-to-Many

Variant (CHILD)
  ├─ id: 298
  ├─ sku: "BIKE-001-RED-M"
  ├─ product_id: 301 ← Foreign Key to Product
  └─ barcode: "123456789"
```

**Key Point**: `Variant.product_id` → points to `Product.id` (parent)

## Database Schema

### `catalog_product` Table
```sql
CREATE TABLE catalog_product (
  id BIGINT PRIMARY KEY,
  code VARCHAR(150) UNIQUE,           -- Product identifier
  product_type_id BIGINT,             -- FK to ProductType
  brand VARCHAR(255),
  model VARCHAR(255),
  status VARCHAR(20),
  default_label VARCHAR(200),
  -- ... other fields
);
```

### `catalog_variant` Table
```sql
CREATE TABLE catalog_variant (
  id BIGINT PRIMARY KEY,
  product_id BIGINT,                  -- FK to catalog_product (PARENT)
  sku VARCHAR(100) UNIQUE,
  barcode VARCHAR(32),
  mpn VARCHAR(64),
  internal_sku TEXT UNIQUE,
  axis_signature TEXT,
  -- ... other fields
  FOREIGN KEY (product_id) REFERENCES catalog_product(id)
);
```

## Django Model Relationship

```python
# Product = PARENT
class Product(models.Model):
    code = models.CharField(max_length=150, unique=True)
    brand = models.CharField(max_length=255)
    # ... other fields

# Variant = CHILD (points to parent)
class Variant(models.Model):
    product = models.ForeignKey(
        Product,                      # ← Points to PARENT
        on_delete=models.CASCADE,
        related_name="variants"       # ← Product.variants.all()
    )
    sku = models.CharField(max_length=100, unique=True)
    # ... other fields
```

## How to Query

### Get all variants for a product (parent → children)
```python
product = Product.objects.get(code="BIKE-001")
variants = product.variants.all()  # All children
```

### Get parent product from variant (child → parent)
```python
variant = Variant.objects.get(sku="BIKE-001-RED-M")
parent = variant.product  # The parent Product
```

## Summary

| Question | Answer |
|----------|--------|
| **Is there a variant table?** | ✅ YES - `catalog_variant` |
| **Does Product refer to variant or parent?** | **Product = PARENT** |
| **Does Variant refer to parent?** | ✅ YES - `variant.product_id` → `Product.id` |
| **Relationship** | **One Product (parent) → Many Variants (children)** |

## Visual Diagram

```
┌─────────────────────┐
│   catalog_product   │  ← PARENT (Family/Group)
│  (Product)          │
├─────────────────────┤
│ id: 301             │
│ code: "BIKE-001"    │
│ brand: "Trek"       │
│ product_type_id: 5  │
└──────────┬──────────┘
           │
           │ product_id (FK)
           │
           ▼
┌─────────────────────┐
│  catalog_variant    │  ← CHILD (Individual SKU)
│  (Variant)          │
├─────────────────────┤
│ id: 298             │
│ product_id: 301 ────┼──→ Points to Product
│ sku: "BIKE-001-RED" │
│ barcode: "123..."   │
└─────────────────────┘
```

## Real Example from Your Database

```
Product (PARENT):
  ID: 301
  Code: "RC14080HDSL-9010-LINE-OB"
  Type: "receveur-de-doucher-à-encastrer"
  Variants: 1 variant

Variant (CHILD):
  ID: 298
  SKU: "RC14080HDSL-9010-LINE-OB"
  product_id: 301 ← Points to Product #301
```

**Answer**: 
- ✅ **Variant table exists**: `catalog_variant`
- ✅ **Product = PARENT** (the family/group)
- ✅ **Variant.product_id** → points to Product (parent)
