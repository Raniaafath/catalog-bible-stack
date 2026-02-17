# Frontend Attribute Mapping Guide

## Overview
The frontend mapping interface has been updated to support **parent-variant product imports** with improved search functionality and clear user instructions.

## Key Features

### 1. **Search for Attributes (No Auto-Suggestions)**
- Each column now has a **search field** to find the right attribute
- Auto-suggestions have been **removed** because they can be incorrect
- **You are in control** - manually search and select the correct mapping

### 2. **Parent Product ID Mapping**
- **New field**: `🔑 Parent Product ID (groups variants)`
- Map your CSV column that contains the parent/group identifier
- Example: If your CSV has a `parent_id` column that groups variants together, map it to "Parent Product ID"

### 3. **Variation Axes Detection**
- The system **automatically detects** which attributes are variation axes (color, size, etc.)
- Shown in the "Variation Axis" column during mapping
- **No manual selection needed** - the system learns from your data

### 4. **Clear Instructions**
- Help panel explains:
  - Parent Product ID: Groups variants together
  - Variant SKU: Unique identifier for each variant
  - Variation Axes: Attributes that differ between variants (auto-detected)
  - Product Fields: Shared data across all variants
  - Variant Attributes: Specific data per variant

## How to Use

### Step 1: Upload Your CSV
Upload a file with parent-variant structure. See [CSV_STRUCTURE_EXAMPLES.md](./CSV_STRUCTURE_EXAMPLES.md) for format options.

### Step 2: Assign Category
Select the product category for this import batch.

### Step 3: Map Columns
For each CSV column:

1. **Identify the column type:**
   - Parent Product ID → Select `🔑 Parent Product ID`
   - Variant SKU → Select `Variant SKU`
   - Product fields (brand, model) → Select matching product field
   - Variant attributes (color, size, price) → Search for attribute

2. **Search for attributes:**
   - Type in the search box to filter attributes
   - Select from filtered results
   - Or create a new attribute if needed

3. **Create new attributes:**
   - Check "Create New" if the attribute doesn't exist
   - System will create it during import

4. **Review variation axes:**
   - System automatically marks columns as variation axes
   - Shown with a checkmark in "Variation Axis" column
   - No action needed - just verify it looks correct

### Step 4: Complete Import
Click "Complete Import" to process the file.

## Mapping Examples

### Example 1: Simple Product with Variants
CSV columns:
- `parent_id` → Map to `🔑 Parent Product ID`
- `sku` → Map to `Variant SKU`
- `brand` → Map to `Product Brand`
- `color` → Search for "color" attribute (will be auto-detected as variation axis)
- `size` → Search for "size" attribute (will be auto-detected as variation axis)
- `price` → Search for "price" attribute

### Example 2: All Variants (No Parent Column)
CSV columns:
- `product_code` → Map to `Product Code` (system groups by this)
- `variant_sku` → Map to `Variant SKU`
- `material` → Search for "material" attribute (variation axis)
- `finish` → Search for "finish" attribute (variation axis)

## What Happens During Import

1. **Grouping**: Variants are grouped by Parent Product ID (or shared fields if no parent ID)
2. **Axis Detection**: System analyzes each attribute to detect variation axes (2-20 unique values)
3. **Storage**: Products, variants, and variation axes are stored in the database
4. **Title Generation**: Later, you can generate variant titles using the stored axes

## Tips

- **Use search**: Type partial attribute names to find matches quickly
- **Check variation axes**: Verify the auto-detected axes make sense for your products
- **Parent ID helps**: Using a parent_id column makes grouping more accurate
- **Review before submitting**: Check the mapping table before clicking "Complete Import"

## Troubleshooting

**Q: I don't see my attribute in the list**
- Use the search box to filter
- Create a new attribute if it doesn't exist

**Q: Wrong columns marked as variation axes**
- This is auto-detected based on data patterns
- Attributes with 2-20 unique values are considered potential axes
- You can adjust after import if needed

**Q: How do I know if my mapping is correct?**
- Check the "Sample Data" column to see what values will be mapped
- Verify variation axes match your product structure
- Ensure Parent Product ID groups variants correctly

## See Also
- [CSV Structure Examples](./CSV_STRUCTURE_EXAMPLES.md) - CSV format options
- [Quick Start Guide](./QUICK_START.md) - Step-by-step tutorial
- [What Import Does](./WHAT_IMPORT_DOES.md) - Technical details

