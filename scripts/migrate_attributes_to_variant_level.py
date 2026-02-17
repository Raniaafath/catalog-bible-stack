#!/usr/bin/env python3
"""
Deterministic script to migrate attribute values from product-level to variant-level.

This script uses ProductTypeAttribute.variant_level as the authoritative source
to determine which attributes should be variant-level.

Usage:
    # Step 1: Mark variant-level attributes (in Admin UI or via script)
    # Step 2: Dry run (see what would be done)
    python manage.py shell < scripts/migrate_attributes_to_variant_level.py
    
    # Step 3: Actually migrate (uncomment the last line or set dry_run=False)
"""

import os
import django
from collections import defaultdict

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from catalog.models import (
    ProductAttributeValue, Product, Variant, Attribute, ProductTypeAttribute
)
from django.db import transaction


def get_variant_level_attributes():
    """
    Get the set of (product_type_id, attribute_id) pairs where variant_level=True.
    
    Returns:
        set: Set of tuples (product_type_id, attribute_id) that should be variant-level
    """
    variant_level_attrs = ProductTypeAttribute.objects.filter(
        variant_level=True
    ).select_related('product_type', 'attribute')
    
    return {
        (pta.product_type_id, pta.attribute_id)
        for pta in variant_level_attrs
    }


def analyze_migration_candidates(variant_level_attrs):
    """
    Analyze what would be migrated.
    
    Returns:
        dict: Analysis report with counts and details
    """
    report = {
        'attributes_by_product_type': defaultdict(lambda: defaultdict(int)),
        'products_to_migrate': defaultdict(set),
        'product_level_values': [],
        'total_product_level_values': 0,
        'total_variants_affected': 0,
        'conflicts': [],
    }
    
    # Get all product-level attribute values
    product_level_values = ProductAttributeValue.objects.filter(
        product_id__isnull=False,
        variant_id__isnull=True
    ).select_related('product', 'product__product_type', 'attribute')
    
    for pav in product_level_values:
        product = pav.product
        product_type_id = product.product_type_id
        attribute_id = pav.attribute_id
        
        # Check if this attribute should be variant-level for this product type
        if (product_type_id, attribute_id) not in variant_level_attrs:
            continue
        
        # This attribute should be migrated
        report['total_product_level_values'] += 1
        report['products_to_migrate'][product_type_id].add(product.id)
        report['attributes_by_product_type'][product_type_id][attribute_id] += 1
        report['product_level_values'].append(pav)
        
        # Check for conflicts (variant already has this attribute)
        variants = Variant.objects.filter(product=product)
        for variant in variants:
            existing_variant_value = ProductAttributeValue.objects.filter(
                variant=variant,
                attribute=pav.attribute
            ).first()
            
            if existing_variant_value:
                report['conflicts'].append({
                    'product_id': product.id,
                    'product_code': product.code,
                    'variant_id': variant.id,
                    'variant_sku': variant.sku,
                    'attribute_code': pav.attribute.code,
                })
            else:
                report['total_variants_affected'] += 1
    
    return report


def print_migration_report(report, variant_level_attrs):
    """Print detailed migration report."""
    print("\n" + "=" * 80)
    print("MIGRATION ANALYSIS REPORT")
    print("=" * 80)
    
    if not variant_level_attrs:
        print("\n⚠️  No variant-level attributes found!")
        print("\nYou need to mark attributes as variant_level=True in ProductTypeAttribute first.")
        print("\nExample attributes that should typically be variant-level:")
        print("  - main_color, color, couleur")
        print("  - length_cm, width_cm, height_cm (if they vary per variant)")
        print("  - size, format, pack_count")
        print("\nTo mark them:")
        print("  1. Go to Admin UI: Product Types → select type → Attributes → set variant_level=True")
        print("  2. Or use Django shell to update ProductTypeAttribute")
        return
    
    print(f"\n✅ Found {len(variant_level_attrs)} variant-level attribute configurations")
    
    # Group by product type and attribute for display
    variant_attrs_by_type = defaultdict(list)
    for product_type_id, attribute_id in variant_level_attrs:
        pta = ProductTypeAttribute.objects.select_related('product_type', 'attribute').get(
            product_type_id=product_type_id,
            attribute_id=attribute_id
        )
        variant_attrs_by_type[pta.product_type.code].append(pta.attribute.code)
    
    print("\nVariant-level attributes by product type:")
    print("-" * 80)
    for product_type_code, attr_codes in sorted(variant_attrs_by_type.items()):
        print(f"  {product_type_code}:")
        for attr_code in sorted(attr_codes):
            print(f"    - {attr_code}")
    
    if report['total_product_level_values'] == 0:
        print("\n✅ No product-level values found that need migration!")
        print("   All variant-level attributes are already at variant-level or don't have values.")
        return
    
    print(f"\n📊 Migration Statistics:")
    print("-" * 80)
    print(f"  Total product-level values to migrate: {report['total_product_level_values']}")
    print(f"  Products affected: {sum(len(products) for products in report['products_to_migrate'].values())}")
    print(f"  Variants that will get new attribute values: {report['total_variants_affected']}")
    print(f"  Conflicts (variant already has value): {len(report['conflicts'])}")
    
    if report['conflicts']:
        print("\n⚠️  Conflicts detected (variants that already have these attributes):")
        print("-" * 80)
        for conflict in report['conflicts'][:10]:  # Show first 10
            print(f"  Product {conflict['product_code']} → Variant {conflict['variant_sku']} already has {conflict['attribute_code']}")
        if len(report['conflicts']) > 10:
            print(f"  ... and {len(report['conflicts']) - 10} more")
    
    # Show breakdown by product type
    if report['attributes_by_product_type']:
        print("\n📋 Breakdown by product type:")
        print("-" * 80)
        for product_type_id, attrs in report['attributes_by_product_type'].items():
            product_type = Product.objects.filter(product_type_id=product_type_id).first()
            if product_type:
                product_type_code = product_type.product_type.code
            else:
                product_type_code = f"type_id={product_type_id}"
            
            print(f"\n  {product_type_code}:")
            for attribute_id, count in sorted(attrs.items()):
                attr = Attribute.objects.get(id=attribute_id)
                products_count = len([
                    p for p in report['product_level_values']
                    if p.product.product_type_id == product_type_id and p.attribute_id == attribute_id
                ])
                print(f"    - {attr.code}: {count} values across {products_count} products")


@transaction.atomic
def migrate_attributes_to_variant_level(variant_level_attrs, dry_run=True):
    """
    Migrate attribute values from product-level to variant-level.
    
    Args:
        variant_level_attrs: Set of (product_type_id, attribute_id) tuples
        dry_run: If True, only show what would be done (don't actually migrate)
    """
    if dry_run:
        print("\n⚠️  DRY RUN MODE - No actual changes will be made\n")
    
    # Get all product-level attribute values for variant-level attributes
    product_level_values = ProductAttributeValue.objects.filter(
        product_id__isnull=False,
        variant_id__isnull=True
    ).select_related('product', 'product__product_type', 'attribute', 'attribute_value')
    
    migrated_count = 0
    skipped_count = 0
    conflict_count = 0
    
    for pav in product_level_values:
        product = pav.product
        product_type_id = product.product_type_id
        attribute_id = pav.attribute_id
        
        # Only migrate if this attribute is marked as variant-level for this product type
        if (product_type_id, attribute_id) not in variant_level_attrs:
            continue
        
        # Get all variants for this product
        variants = Variant.objects.filter(product=product)
        
        if not variants.exists():
            if not dry_run:
                print(f"  ⚠️  Product {product.code} has no variants - skipping attribute {pav.attribute.code}")
            skipped_count += 1
            continue
        
        # Copy to each variant (skip if variant already has this attribute)
        for variant in variants:
            # Check if variant already has this attribute
            existing = ProductAttributeValue.objects.filter(
                variant=variant,
                attribute=pav.attribute
            ).first()
            
            if existing:
                if not dry_run:
                    print(f"  ⚠️  Variant {variant.sku} already has {pav.attribute.code} - skipping")
                conflict_count += 1
                continue
            
            # Copy all fields exactly
            if dry_run:
                print(f"  Would create: Variant {variant.sku} ← {pav.attribute.code} (from Product {product.code})")
            else:
                ProductAttributeValue.objects.create(
                    variant=variant,
                    product=None,  # Clear product_id
                    attribute=pav.attribute,
                    attribute_value=pav.attribute_value,
                    value_text=pav.value_text,
                    value_number=pav.value_number,
                    value_bool=pav.value_bool,
                    value_json=pav.value_json,
                    unit=pav.unit,
                    is_axis=pav.is_axis,
                )
                migrated_count += 1
        
        # Delete the product-level attribute value
        if not dry_run:
            pav.delete()
            print(f"  ✓ Migrated {pav.attribute.code} from Product {product.code} to {variants.count()} variant(s)")
    
    if not dry_run:
        print(f"\n✅ Migration complete!")
        print(f"   - Migrated {migrated_count} attribute values to variant-level")
        print(f"   - Skipped {skipped_count} (no variants)")
        print(f"   - Conflicts {conflict_count} (variant already had value)")
    else:
        print(f"\n⚠️  DRY RUN COMPLETE")
        print(f"   - Would migrate {product_level_values.count()} product-level values")
        print(f"   - Run with dry_run=False to perform actual migration")


def verify_migration(attribute_codes=None):
    """
    Verify migration results.
    
    Args:
        attribute_codes: List of attribute codes to check (if None, checks all variant-level attributes)
    """
    print("\n" + "=" * 80)
    print("VERIFICATION")
    print("=" * 80)
    
    # Count variant-level values
    variant_level_count = ProductAttributeValue.objects.filter(
        variant_id__isnull=False,
        product_id__isnull=True
    ).count()
    
    print(f"\n✅ Variant-level attribute values: {variant_level_count}")
    
    # Check if migrated attributes are still at product-level
    if attribute_codes:
        remaining_product_level = ProductAttributeValue.objects.filter(
            product_id__isnull=False,
            variant_id__isnull=True,
            attribute__code__in=attribute_codes
        ).select_related('product', 'attribute')
        
        if remaining_product_level.exists():
            print(f"\n⚠️  Found {remaining_product_level.count()} product-level values for migrated attributes:")
            for pav in remaining_product_level[:10]:
                print(f"   - Product {pav.product.code} still has {pav.attribute.code} at product-level")
            if remaining_product_level.count() > 10:
                print(f"   ... and {remaining_product_level.count() - 10} more")
        else:
            print("\n✅ No product-level values found for migrated attributes - all moved!")


if __name__ == "__main__":
    print("=" * 80)
    print("ATTRIBUTE MIGRATION SCRIPT")
    print("=" * 80)
    print("\nThis script migrates attribute values from product-level to variant-level")
    print("based on ProductTypeAttribute.variant_level=True configuration.")
    
    # Step 1: Get variant-level attributes
    variant_level_attrs = get_variant_level_attributes()
    
    # Step 2: Analyze what would be migrated
    report = analyze_migration_candidates(variant_level_attrs)
    
    # Step 3: Print detailed report
    print_migration_report(report, variant_level_attrs)
    
    if variant_level_attrs and report['total_product_level_values'] > 0:
        # Step 4: Dry run migration
        print("\n" + "=" * 80)
        migrate_attributes_to_variant_level(variant_level_attrs, dry_run=True)
        
        # Step 5: Instructions for actual migration
        print("\n" + "=" * 80)
        print("\nTo perform the actual migration:")
        print("  1. Review the report above carefully")
        print("  2. Run this script again and uncomment the line below, or")
        print("  3. Run in Django shell:")
        print("     >>> migrate_attributes_to_variant_level(variant_level_attrs, dry_run=False)")
        print("\n" + "=" * 80)
        
        # Uncomment to automatically perform migration:
        # migrate_attributes_to_variant_level(variant_level_attrs, dry_run=False)
        # verify_migration(attribute_codes=['main_color', 'length_cm', 'width_cm', 'height_cm'])
