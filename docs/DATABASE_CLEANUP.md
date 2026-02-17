# Database Cleanup and Organization Guide

## Overview

The `cleanup_database` management command helps you maintain a clean and organized database structure by:

1. **Identifying orphaned records** - Records with broken foreign key relationships
2. **Validating data integrity** - Checking for invalid references and inconsistencies
3. **Removing invalid data** - Cleaning up records that violate constraints
4. **Reporting issues** - Providing detailed reports on database health

## Usage

### Preview Changes (Dry Run)

```bash
python manage.py cleanup_database --dry-run
```

This shows what issues exist without making any changes.

### Detailed Preview

```bash
python manage.py cleanup_database --dry-run --verbose
```

Shows detailed information about each issue found.

### Auto-Fix Issues

```bash
python manage.py cleanup_database --fix
```

Automatically fixes issues where possible (orphaned records, invalid references).

### Preview + Auto-Fix

```bash
python manage.py cleanup_database --dry-run --fix --verbose
```

## What Gets Checked

### 1. Orphaned Records
- **ProductAttributeValue**: Records with both `product` and `variant` null, or both set (violates constraint)
- **Variant**: Variants without a valid product reference
- **ProductVariantAxis**: Axes referencing non-existent products
- **ChannelVariantAxis**: Channel-specific axes with invalid product references
- **ChannelListingAxis**: Listing axes with invalid listing references
- **ChannelListingMap**: Maps with null variant or listing
- **BundleComponent**: Bundle components with invalid variant references
- **ImportRow**: Import rows without a valid ProductImport
- **CategoryBatch**: Batches without a valid ProductImport
- **AttributeMapping**: Mappings without a valid CategoryBatch

### 2. Invalid References
- ProductAttributeValue with invalid product/variant foreign keys
- Variants with invalid product references
- Products with invalid product_type references
- BundleComponents with invalid variant references
- ChannelListingMap with invalid variant references

### 3. Duplicate Records
- Duplicate SKUs (should be unique)
- Duplicate product codes (should be unique)

### 4. Empty/Unused Records
- Products without variants
- ProductTypes without products
- Attributes without values

## What Gets Fixed Automatically

When using `--fix`, the command will:

✅ **Delete orphaned records** - Remove records with broken foreign keys
✅ **Remove invalid references** - Clean up records pointing to non-existent entities
✅ **Fix constraint violations** - Remove records that violate database constraints

⚠️ **Requires manual review:**
- Duplicate records (need manual deduplication)
- Empty/unused records (may be intentional)

## Example Output

```
🔍 DRY RUN MODE - No changes will be made

Analyzing database structure...
  Checking ProductAttributeValue...
    ⚠️  Found 5 invalid records
  Checking Variants...
  Checking Products...
  Checking Variant Axes...
  Checking BundleComponents...
  Checking ChannelListingAxis...
  Checking ChannelListingMap...
  Checking Products without variants...
    ⚠️  Found 12 products without variants
  Checking ProductTypes...
  Checking Attributes...
  Checking ProductTypeAttributes...
  Checking Import records...
  Checking for duplicate SKUs...
  ✓ Analysis complete

================================================================================
DATABASE CLEANUP REPORT
================================================================================

🔴 ORPHANED RECORDS (broken foreign keys):
  • ProductAttributeValue: 5 records

🟡 EMPTY/UNUSED RECORDS:
  • Product.no_variants: 12 records

📊 Total issues found: 17

To automatically fix issues, run with --fix flag
```

## Integration with Existing Cleanup Scripts

This command complements the existing cleanup scripts:

- **`clean_database.py`** - Complete database wipe (removes all data)
- **`clean_everything.py`** - Removes all catalog data
- **`clean_catalog_data.py`** - Removes products/variants but preserves structure

**`cleanup_database.py`** is different - it:
- Preserves valid data
- Only removes invalid/orphaned records
- Validates and reports on database health
- Can be run regularly to maintain database integrity

## Best Practices

1. **Run regularly** - Schedule this command to run periodically (e.g., weekly)
2. **Use dry-run first** - Always preview changes before applying them
3. **Review reports** - Check the report to understand what will be cleaned
4. **Backup first** - Always backup before running with `--fix` in production
5. **Monitor empty records** - Empty/unused records may be intentional, review before deleting

## Common Scenarios

### After Import Errors
If an import fails partway through, you may have orphaned records:
```bash
python manage.py cleanup_database --fix
```

### Before Major Operations
Before running migrations or bulk operations:
```bash
python manage.py cleanup_database --dry-run
```

### Regular Maintenance
Add to your maintenance routine:
```bash
python manage.py cleanup_database --fix --verbose
```

## Troubleshooting

### "No issues found"
✅ Your database is clean! No action needed.

### "Orphaned records found"
These are records with broken foreign keys. Safe to delete with `--fix`.

### "Duplicate records found"
These need manual review. The command will report which records are duplicated.

### "Empty records found"
These may be intentional (e.g., product types ready for future use). Review before deleting.

## Related Commands

- `python manage.py clean_database` - Complete database wipe
- `python manage.py run_pipeline` - Run import pipeline
- `python manage.py migrate` - Apply database migrations
