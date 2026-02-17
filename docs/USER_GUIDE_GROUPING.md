# Product Grouping User Guide

This guide explains how to group product variants into products (groups/families) for different marketplaces.

## Overview

In this system:
- **Variants** are individual sellable items (SKUs) with specific attributes like color, size, etc.
- **Products (Groups)** are containers that group related variants together
- **Channel/Marketplace** determines how variants are grouped and which attributes are used as variation axes

## Quick Start Workflow

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  1. Import CSV   │ ──▶ │  2. Select       │ ──▶ │  3. Group with   │
│     Variants     │     │     Variants     │     │     Axes         │
└──────────────────┘     └──────────────────┘     └──────────────────┘
                                                            │
                                                            ▼
                                                  ┌──────────────────┐
                                                  │  4. Manage in    │
                                                  │  Listing Groups  │
                                                  └──────────────────┘
```

---

## Step 1: Import Variants

### Navigate to Imports
1. Go to **Imports** in the sidebar menu
2. Click **New Import**

### Upload Your File
1. Select your CSV or Excel file containing product data
2. Each row in your file will become a **variant**

### Example CSV Structure
```csv
sku,brand,title,color,size,price
TSH-BLK-S,StyleCo,T-Shirt Premium,Black,S,29.99
TSH-BLK-M,StyleCo,T-Shirt Premium,Black,M,29.99
TSH-BLK-L,StyleCo,T-Shirt Premium,Black,L,29.99
TSH-WHT-S,StyleCo,T-Shirt Premium,White,S,29.99
TSH-WHT-M,StyleCo,T-Shirt Premium,White,M,29.99
```

### What Happens After Import
- Each row becomes a **variant** with its own placeholder product
- Variants are marked as "Ungrouped" initially
- You can now select variants to group them together

---

## Step 2: Select Variants to Group

### Navigate to Variants
1. Go to **Products** → **Variants** in the sidebar menu
2. You'll see a list of all your variants

### Use the Filter
The filter dropdown lets you quickly find variants:
- **All**: Show all variants
- **Grouped**: Show only variants that are in a product group
- **Ungrouped**: Show only standalone variants

### Select Variants
1. Click the checkbox next to each variant you want to group
2. Or click the header checkbox to select all visible variants
3. A selection bar appears showing how many variants are selected

### Tips for Selecting
- Group variants that belong to the same product family (e.g., same T-shirt in different colors/sizes)
- Typically 2-10 variants make a good product group
- Variants should share some attributes (brand, material) but differ in others (color, size)

---

## Step 3: Group with Variation Axes

### Open the Grouping Dialog
1. With 2+ variants selected, click **Group into Product** or **Group Selected**
2. The grouping dialog opens

### Select a Marketplace
1. Choose the marketplace/channel (e.g., Shopify, Amazon, eBay)
2. Different marketplaces can have different variation axes

### Review Detected Differences
The system automatically analyzes your selected variants and shows:

**Differences** (attributes that vary between variants):
- These are candidates for variation axes
- Recommended axes have 2-10 unique values and no missing data

**Common Attributes** (same across all variants):
- These are shared properties like brand, material, etc.

### Select Variation Axes
1. Check the boxes next to attributes you want as variation axes
2. Common choices: Color, Size, Material, Pack Count
3. The order matters - first axis appears first in titles

**Example:**
```
✅ color (2 values: Black, White)     ← First axis
✅ size (3 values: S, M, L)           ← Second axis
☐ price (2 values: 29.99, 34.99)     ← Not selected (price isn't typically an axis)
```

### Set Product Code
1. Enter a unique code for your product group (e.g., "tshirt-premium")
2. This identifies the product family

### Create the Group
1. Click **Create Product Group**
2. All selected variants are moved to the new product
3. Variation axes are saved for the selected channel

---

## Step 4: Manage in Listing Groups

### Navigate to Listing Groups
1. Go to **Listing Groups** in the sidebar menu
2. Find your newly created listing

### View Listing Details
Click on a listing to see:
- **Variants Tab**: All variants in this listing
- **Variation Axes Tab**: Which attributes define variations

### Add More Variants
1. Click **Add Variants** in the Variants tab
2. Select additional variants from the same product
3. Click **Add** to include them in the listing

### Modify Axes
1. Go to the **Variation Axes** tab
2. The system analyzes differences and suggests axes
3. Check/uncheck axes as needed
4. Click **Save Axes** to update

---

## Ungrouping Variants

If you need to reorganize variants:

### Select Variants to Ungroup
1. Go to **Variants** page
2. Select the variants you want to ungroup
3. Variants must be in an existing group (not already ungrouped)

### Click Ungroup
1. The **Ungroup** button appears when grouped variants are selected
2. Click **Ungroup Selected**
3. Each variant moves to its own placeholder product
4. Empty product groups are automatically deleted

### Regroup Differently
After ungrouping, you can:
1. Select different combinations of variants
2. Group them into new products with different axes

---

## Understanding the Data Model

### Products (Groups)
- Act as containers for related variants
- Hold marketplace-specific configuration
- One product can have different axes per marketplace

### Variants
- Individual sellable items with unique SKUs
- Contain attribute values (color, size, etc.)
- Always belong to one product

### Variation Axes
- Define which attributes differentiate variants
- Stored per product + channel combination
- Used for generating variant-specific titles

```
Product: "T-Shirt Premium"
├── Shopify Channel
│   └── Axes: Color, Size
├── eBay Channel
│   └── Axes: Color only
└── Variants
    ├── TSH-BLK-S (Black, Small)
    ├── TSH-BLK-M (Black, Medium)
    ├── TSH-WHT-S (White, Small)
    └── TSH-WHT-M (White, Medium)
```

---

## FAQ

### Q: How many variants should I group together?
A: Typically 2-10 variants per group. This depends on your product and marketplace requirements.

### Q: Can I have different groupings per marketplace?
A: Yes! Each marketplace can have its own listing with different axes. Use Listing Groups to manage this.

### Q: What happens to orphaned products?
A: When you ungroup variants, empty products are automatically deleted to keep your catalog clean.

### Q: Can I change variation axes after grouping?
A: Yes, go to the Listing Group detail page and modify axes in the Variation Axes tab.

### Q: Why is "Ungrouped" showing for my variants?
A: Variants are ungrouped when they're in placeholder products (created during import). Group them to organize your catalog.

---

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Select all visible | Click header checkbox |
| Clear selection | Click header checkbox again |

---

## Best Practices

1. **Import first, group later**: Import all variants, then organize them into groups
2. **Use meaningful product codes**: Makes it easier to find and manage products
3. **Choose axes carefully**: Pick attributes that customers use to select variants
4. **Keep groups manageable**: Very large groups (50+ variants) may be hard to manage
5. **Review before grouping**: Use the comparison dialog to verify differences

---

## Troubleshooting

### "Need at least 2 variants to compare"
Select at least 2 variants before clicking Group.

### "Channel not found"
Make sure you have channels configured in your system.

### No differences detected
The selected variants may have identical attributes. Check your data.

### Ungroup button not appearing
The button only appears when grouped variants are selected. Filter by "Grouped" to find them.
