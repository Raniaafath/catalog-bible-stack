# Testing Products – Structured Guide

This guide describes how to add **testing products** to the catalog (e.g. receveurs de douche, radiateurs) in a clear, repeatable way.

---

## 1. Recommended approach

1. **Use the CSV import** (Imports → New import) with the provided example files.
2. **Use clear column names** that the importer can auto-detect (see below).
3. **One CSV per product type** (e.g. receveurs only, or radiators only) to keep category mapping simple.

---

## 2. Column names the importer recognises

The first row of your CSV must be headers. These names are **auto-mapped** to roles:

| Column name (any case)      | Role        | Use |
|----------------------------|-------------|-----|
| `parent_id`, `product_id`, `group_id`, `parent_sku`, `model` | **Product key** | Group variants into one product when grouping is enabled |
| `sku`, `variant_sku`, `ean`, `barcode`, `gtin`              | **Variant key** | Unique identifier for the row (SKU preferred) |
| `barcode` (literal)                                        | **Barcode**     | Stored in variant EAN/barcode (also used if no BARCODE rule) |
| `category`, `product_type`, `categorie`, `cat`              | **Category**   | Product type / category (assign in step “Assign category”) |
| `brand`, `manufacturer`, `marque`                           | **Brand**      | Product brand |
| `title`, `name`, `product_name`, `nom`, `designation`      | **Title**      | Variant/product title |
| `description`, `desc`, `body_html`, `details`               | **Description**| Long description (HTML allowed) |

Any other column is treated as an **attribute**. To create attributes from them, in the import column mapping set **“Create attribute”** with a name (e.g. `color` → attribute code `color`).

---

## 3. Example CSV structure (minimal)

```csv
parent_id,sku,barcode,brand,title,description,category,color,material,dimensions_cm,weight_kg
RECEV-LINE-9010,RC14080HDSL-9010-LINE-OB,4262493813932,ONBATH'S,Receveur résine 140 x 80 cm blanc...,"<p>Description...</p>",Receveur de douche,Blanc,Résine,140 x 80,40
RECEV-LINE-9010,RC16080HDSL-9010-LINE-OB,4262493813949,ONBATH'S,Receveur résine 160 x 80 cm blanc...,"<p>Description...</p>",Receveur de douche,Blanc,Résine,160 x 80,40
```

- **System columns**: `parent_id`, `sku`, `barcode`, `brand`, `title`, `description`, `category`.
- **Attribute columns**: `color`, `material`, `dimensions_cm`, `weight_kg` (and any others you add). Use short, clear names (e.g. `color`, `material`, `power_w`, `dimensions_cm`).

---

## 4. Provided test files

| File | Content |
|------|--------|
| `docs/examples/receveurs_douche_test.csv` | Receveurs de douche (résine, plusieurs dimensions/couleurs) |
| `docs/examples/radiateurs_test.csv`       | Radiateurs électriques (plusieurs modèles/puissances) |
| `docs/examples/COLUMN_MAPPING_RECEVEURS_RADIATEURS.md` | Mapping from your source column names to the recommended CSV headers |

Use the CSV files as templates: same column names, add or remove rows as needed. Use the mapping doc to translate a full export (e.g. from your PIM) into the clear column names above.

---

## 5. Import steps (UI)

1. **Imports** → **New import** → upload CSV (or XLSX).
2. **Parse**: column roles are guessed from headers; fix if needed.
3. **Assign category**: choose or enter the category (e.g. “Receveur de douche” or “Radiateur électrique”). This becomes the ProductType.
4. **Column mapping**: for each attribute column, set **“Create attribute”** with the desired attribute name (e.g. `color`, `material`, `dimensions_cm`). Optional: create these attributes in Catalog → Attributes first, then map to **existing** attribute.
5. **Preview** → **Process** to create products and variants.

---

## 6. Grouping behaviour

- **Group by product key** (recommended for receveurs/radiateurs): enable “Group by product key” and use the same `parent_id` for all variants of one product (e.g. same receveur line, different sizes). One Product is created per `parent_id`; each row is one Variant.
- **Standalone**: if you leave “Group by product key” off, each row becomes one Product with one Variant (for manual grouping later).

---

## 7. Attribute column naming (good practice)

- Prefer **short, clear names**: `color`, `material`, `power_w`, `dimensions_cm`, `weight_kg`, `installation_type`.
- Avoid long internal codes in headers (e.g. `feature_09953_201010|RECEVEUR_...`) for testing; map those in a separate “production” import if needed.

---

## 8. Quick reference – column → role

| If your source has…           | Put in CSV as | Role (auto)   |
|------------------------------|---------------|---------------|
| Catégorie du produit         | `category`   | Category      |
| Identifiant produit / SKU    | `sku`        | Variant key   |
| Code parent                  | `parent_id`  | Product key   |
| EAN / GTIN                   | `barcode`    | Barcode       |
| Marque                       | `brand`      | Brand         |
| Titre FR                     | `title`      | Title         |
| Description longue FR        | `description`| Description   |
| Couleur / Matière / Dimensions / etc. | `color`, `material`, `dimensions_cm`, … | Attribute (map to “Create attribute”) |

You can add more attribute columns with the same naming style; keep one header row and consistent names for a clean, structured way of testing.
