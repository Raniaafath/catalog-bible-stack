# How to Add a Product to the Database

## ✅ No Migrations Needed (for variant endpoints)

The variant endpoint changes we just made **don't require migrations** because:
- We only modified API views/serializers
- No database schema changes (models unchanged)
- Existing `Product` and `Variant` tables work as-is

---

## Ways to Add a Product

### Option 1: Via API (Recommended for Frontend)

**Endpoint**: `POST /api/v1/products/`

**Request Body**:
```json
{
  "product_type_id": 1,
  "code": "PROD-001",
  "status": "draft",
  "brand": "Nike",
  "model": "Air Max",
  "default_label": "Nike Air Max Running Shoe",
  "series": "Running",
  "source_title": "Nike Air Max",
  "source_description": "Comfortable running shoe",
  "source_locale": "en",
  "source_supplier": "Supplier Name",
  "source_sku": "SUP-001",
  "attributes": {
    "color": "red",
    "material": "leather"
  }
}
```

**Required Fields**:
- `product_type_id` (must exist)
- `code` (must be unique)

**Then Add Variants**:
```bash
POST /api/v1/products/{product_id}/variants/
{
  "sku": "PROD-001-RED-42",
  "barcode": "1234567890123",
  "mpn": "MPN-001"
}
```

---

### Option 2: Via Django Admin

1. Go to: `http://your-domain/admin/`
2. Navigate to: **Catalog → Products**
3. Click **"Add Product"**
4. Fill in:
   - **Product Type** (required)
   - **Code** (required, unique)
   - **Status** (default: draft)
   - Other fields (optional)
5. Click **"Save"**

**To add variants in admin**:
- Go to **Catalog → Variants**
- Click **"Add Variant"**
- Select the **Product** from dropdown
- Fill in SKU, barcode, MPN

---

### Option 3: Via Django Shell

```python
from catalog.models import Product, ProductType, Variant

# Get or create a product type
product_type = ProductType.objects.get(code="shoes")  # or create one

# Create product
product = Product.objects.create(
    product_type=product_type,
    code="PROD-001",
    status="draft",
    brand="Nike",
    model="Air Max",
    default_label="Nike Air Max Running Shoe"
)

# Create variant
variant = Variant.objects.create(
    product=product,
    sku="PROD-001-RED-42",
    barcode="1234567890123",
    mpn="MPN-001"
)
```

---

### Option 4: Via Import (CSV/Excel)

1. Go to frontend: **Imports → Upload File**
2. Upload CSV with columns:
   - `parent_id` or `product_id` (for grouping)
   - `sku` (variant SKU)
   - `category` (maps to ProductType)
   - `brand`, `model`, etc.
3. Map attributes
4. Process import

**Note**: Currently import auto-groups by `parent_id`. We'll modify this later to create standalone products.

---

## Quick Test via API

```bash
# 1. List product types (to get an ID)
curl -H "Authorization: Token YOUR_TOKEN" \
  https://bib.neomarkgroup.fr/api/v1/product-types/

# 2. Create product
curl -X POST \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product_type_id": 1,
    "code": "TEST-001",
    "status": "draft",
    "brand": "Test Brand"
  }' \
  https://bib.neomarkgroup.fr/api/v1/products/

# 3. Add variant
curl -X POST \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sku": "TEST-001-V1",
    "barcode": "123456789"
  }' \
  https://bib.neomarkgroup.fr/api/v1/products/{product_id}/variants/
```

---

## Required: ProductType Must Exist First

Before creating a product, you need a `ProductType`:

```python
# Via Django shell
from catalog.models import ProductType

ProductType.objects.create(
    code="shoes",
    default_label="Shoes",
    is_active=True
)
```

Or via API:
```bash
# But ProductTypeViewSet is ReadOnly, so use admin or shell
```

---

## Summary

- ✅ **No migrations needed** for variant endpoints
- ✅ **Add product** via API: `POST /api/v1/products/`
- ✅ **Add variant** via API: `POST /api/v1/products/{id}/variants/`
- ✅ **Or use Django Admin** for manual entry
- ⚠️ **ProductType must exist first** (create via admin or shell)
