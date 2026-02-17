# Column mapping – Source export → Testing CSV

When you have a full export with internal column names (e.g. from your PIM), map them to the **clear column names** used in the testing CSV so the importer can auto-detect roles.

## Receveurs de douche / Radiateurs

| Source (example) | Use in CSV | Role |
|------------------|------------|------|
| `product_category` / Catégorie du produit | `category` | Category |
| `shop_sku` / Identifiant produit | `sku` | Variant key |
| `parentproductid` / Code parent | `parent_id` | Product key |
| `gtin_EAN13` / EAN | `barcode` | Barcode |
| `feature_06575_brand` / Marque | `brand` | Brand |
| `i18n_fr_12963_title` / Titre du produit FR | `title` | Title |
| `i18n_fr_01022_longdescription` / Description longue FR | `description` | Description |
| `feature_10837_main_color` / Couleur principale | `color` | Attribute |
| `feature_10840_main_material` / Matière principale | `material` | Attribute |
| Dimensions (L. x l.) / Longueur etc. | `dimensions_cm` | Attribute |
| Poids du produit nu | `weight_kg` | Attribute |
| Type de pose | `installation_type` | Attribute |
| Référence commerciale / Code à usage interne | `product_reference` | Attribute |
| Puissance (en W) | `power_w` | Attribute (radiateurs) |

Keep one header row and one consistent set of names per import (e.g. always `sku`, `barcode`, `title`) for a **structured way for testing**.
