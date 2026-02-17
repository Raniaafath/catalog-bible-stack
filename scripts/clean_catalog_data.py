#!/usr/bin/env python3
"""
Safely clean catalog data while preserving structure.

This script removes:
- All ProductAttributeValue records (attribute values)
- All Variant records
- All Product records

But preserves:
- ProductType (product type definitions)
- Attribute (attribute definitions)
- AttributeValue (attribute value definitions)
- ProductTypeAttribute (attribute associations with product types)
- Channels (marketplace definitions)
- All other structural data

Usage:
    python manage.py shell < scripts/clean_catalog_data.py
    
Or:
    python manage.py shell
    >>> exec(open('scripts/clean_catalog_data.py').read())
"""

import os
import django
from django.db import transaction

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from catalog.models import (
    ProductAttributeValue, Product, Variant,
    ProductType, Attribute, AttributeValue, ProductTypeAttribute,
    BundleComponent,
)
from pub.models import ChannelListingMap


def print_summary():
    """Print current data summary."""
    print("\n" + "=" * 80)
    print("CURRENT DATA SUMMARY")
    print("=" * 80)
    
    product_count = Product.objects.count()
    variant_count = Variant.objects.count()
    attr_value_count = ProductAttributeValue.objects.count()
    product_level_count = ProductAttributeValue.objects.filter(
        product_id__isnull=False, variant_id__isnull=True
    ).count()
    variant_level_count = ProductAttributeValue.objects.filter(
        variant_id__isnull=False, product_id__isnull=True
    ).count()
    listing_map_count = ChannelListingMap.objects.count()
    
    print(f"\n📊 Current Data:")
    print(f"  Products: {product_count}")
    print(f"  Variants: {variant_count}")
    print(f"  ProductAttributeValue: {attr_value_count}")
    print(f"    - Product-level: {product_level_count}")
    print(f"    - Variant-level: {variant_level_count}")
    print(f"  ChannelListingMap: {listing_map_count}")
    
    # Structure that will be preserved
    product_type_count = ProductType.objects.count()
    attribute_count = Attribute.objects.count()
    attribute_value_count = AttributeValue.objects.count()
    pta_count = ProductTypeAttribute.objects.count()
    
    print(f"\n📋 Structure (will be preserved):")
    print(f"  ProductType: {product_type_count}")
    print(f"  Attribute: {attribute_count}")
    print(f"  AttributeValue: {attribute_value_count}")
    print(f"  ProductTypeAttribute: {pta_count}")
    
    return {
        'product_count': product_count,
        'variant_count': variant_count,
        'attr_value_count': attr_value_count,
        'listing_map_count': listing_map_count,
    }


def clean_catalog_data(dry_run=True):
    """
    Clean catalog data while preserving structure.
    
    Args:
        dry_run: If True, only show what would be done (don't actually clean)
    """
    summary = print_summary()
    
    if summary['product_count'] == 0 and summary['variant_count'] == 0:
        print("\n✅ No data to clean - database is already empty!")
        return
    
    print("\n" + "=" * 80)
    print("CLEANUP PLAN")
    print("=" * 80)
    
    if dry_run:
        print("\n⚠️  DRY RUN MODE - No actual changes will be made\n")
        print("Would delete:")
        print(f"  - {summary['attr_value_count']} ProductAttributeValue records")
        print(f"  - {summary['listing_map_count']} ChannelListingMap records")
        print(f"  - {summary['variant_count']} Variant records")
        print(f"  - {summary['product_count']} Product records")
        print("\nWill preserve:")
        print("  - ProductType (product type definitions)")
        print("  - Attribute (attribute definitions)")
        print("  - AttributeValue (attribute value definitions)")
        print("  - ProductTypeAttribute (attribute associations)")
        print("  - Channel (marketplace definitions)")
        print("  - All other structural data")
    else:
        print("\n⚠️  ACTUAL CLEANUP MODE - This will delete data!\n")
        print("Will delete:")
        print(f"  - {summary['attr_value_count']} ProductAttributeValue records")
        print(f"  - {summary['listing_map_count']} ChannelListingMap records")
        print(f"  - {summary['variant_count']} Variant records")
        print(f"  - {summary['product_count']} Product records")
    
    if not dry_run:
        print("\n" + "=" * 80)
        print("CLEANING DATA...")
        print("=" * 80)
        
        with transaction.atomic():
            # Step 1: Delete ProductAttributeValue (has FKs to Product and Variant)
            deleted_attr_values = ProductAttributeValue.objects.all().delete()
            print(f"  ✓ Deleted {deleted_attr_values[0]} ProductAttributeValue records")
            
            # Step 2: Delete BundleComponent (has FK to Variant - PROTECT)
            deleted_bundles = BundleComponent.objects.all().delete()
            print(f"  ✓ Deleted {deleted_bundles[0]} BundleComponent records")
            
            # Step 3: Delete ChannelListingMap (has FK to Variant)
            deleted_listings = ChannelListingMap.objects.all().delete()
            print(f"  ✓ Deleted {deleted_listings[0]} ChannelListingMap records")
            
            # Step 4: Delete Variants (has FK to Product)
            deleted_variants = Variant.objects.all().delete()
            print(f"  ✓ Deleted {deleted_variants[0]} Variant records")
            
            # Step 5: Delete Products
            deleted_products = Product.objects.all().delete()
            print(f"  ✓ Deleted {deleted_products[0]} Product records")
            
            print("\n✅ Cleanup complete!")
            
            # Verify
            print("\n" + "=" * 80)
            print("VERIFICATION")
            print("=" * 80)
            remaining_products = Product.objects.count()
            remaining_variants = Variant.objects.count()
            remaining_attr_values = ProductAttributeValue.objects.count()
            
            print(f"\n✅ Remaining Products: {remaining_products} (should be 0)")
            print(f"✅ Remaining Variants: {remaining_variants} (should be 0)")
            print(f"✅ Remaining ProductAttributeValue: {remaining_attr_values} (should be 0)")
            
            # Show preserved structure
            product_type_count = ProductType.objects.count()
            attribute_count = Attribute.objects.count()
            pta_count = ProductTypeAttribute.objects.count()
            
            print(f"\n📋 Preserved Structure:")
            print(f"  ✅ ProductType: {product_type_count}")
            print(f"  ✅ Attribute: {attribute_count}")
            print(f"  ✅ ProductTypeAttribute: {pta_count}")
            
            if remaining_products == 0 and remaining_variants == 0 and remaining_attr_values == 0:
                print("\n✅ Database is clean and ready for fresh import!")
            else:
                print("\n⚠️  Warning: Some data still remains!")


if __name__ == "__main__":
    print("=" * 80)
    print("CATALOG DATA CLEANUP SCRIPT")
    print("=" * 80)
    print("\nThis script will remove all products, variants, and attribute values")
    print("while preserving product types, attributes, and associations.")
    
    # Run dry run first
    clean_catalog_data(dry_run=True)
    
    print("\n" + "=" * 80)
    print("\nTo perform the actual cleanup:")
    print("  1. Review the summary above carefully")
    print("  2. Uncomment the line below, or")
    print("  3. Run in Django shell:")
    print("     >>> clean_catalog_data(dry_run=False)")
    print("\n" + "=" * 80)
    
    # Uncomment to actually clean:
    # clean_catalog_data(dry_run=False)
