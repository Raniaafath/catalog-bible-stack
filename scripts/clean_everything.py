#!/usr/bin/env python3
"""
Complete cleanup script - deletes ALL catalog data.

This script removes:
- All ProductAttributeValue records
- All Variant records
- All Product records
- All BundleComponent records
- All ProductTypeAttribute records
- All ProductVariantAxis records
- All ChannelVariantAxis records
- All ChannelListingAxis records
- All ChannelListing records
- All ChannelListingMap records
- All AttributeValue records
- All Attribute records
- All ProductType records

This gives you a completely clean database for fresh import.

Usage:
    python manage.py shell < scripts/clean_everything.py
    
Or:
    python manage.py shell
    >>> exec(open('scripts/clean_everything.py').read())
"""

import os
import django
from django.db import transaction

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from catalog.models import (
    ProductAttributeValue, Product, Variant,
    ProductType, Attribute, AttributeValue, ProductTypeAttribute,
    ProductVariantAxis, ChannelVariantAxis, BundleComponent,
)
from catalog.models import ChannelListingAxis
from pub.models import ChannelListingMap, ChannelListing

# Check if kw app is available
try:
    from kw.models import AttributeMap
    KW_AVAILABLE = True
except ImportError:
    KW_AVAILABLE = False
    AttributeMap = None

# Check if importer app is available
try:
    from importer.models import AttributeMapping
    IMPORTER_AVAILABLE = True
except ImportError:
    IMPORTER_AVAILABLE = False
    AttributeMapping = None

# Check if pub app has TemplatePart, Template, PlannerRun, PlannerSeed
try:
    from pub.models import TemplatePart, Template
    TEMPLATE_PART_AVAILABLE = True
except ImportError:
    TEMPLATE_PART_AVAILABLE = False
    TemplatePart = None
    Template = None

try:
    from pub.models import PlannerRun
    PLANNER_RUN_AVAILABLE = True
except (ImportError, AttributeError):
    try:
        from kw.models import PlannerRun
        PLANNER_RUN_AVAILABLE = True
    except (ImportError, AttributeError):
        PLANNER_RUN_AVAILABLE = False
        PlannerRun = None

try:
    from kw.models import PlannerSeed
    PLANNER_SEED_AVAILABLE = True
except ImportError:
    PLANNER_SEED_AVAILABLE = False
    PlannerSeed = None


def print_summary():
    """Print current data summary."""
    print("\n" + "=" * 80)
    print("CURRENT DATA SUMMARY")
    print("=" * 80)
    
    counts = {
        'products': Product.objects.count(),
        'variants': Variant.objects.count(),
        'product_attr_values': ProductAttributeValue.objects.count(),
        'product_types': ProductType.objects.count(),
        'attributes': Attribute.objects.count(),
        'attribute_values': AttributeValue.objects.count(),
        'product_type_attrs': ProductTypeAttribute.objects.count(),
        'product_variant_axes': ProductVariantAxis.objects.count(),
        'channel_variant_axes': ChannelVariantAxis.objects.count(),
        'channel_listing_axes': ChannelListingAxis.objects.count(),
        'channel_listings': ChannelListing.objects.count(),
        'channel_listing_maps': ChannelListingMap.objects.count(),
        'bundle_components': BundleComponent.objects.count(),
    }
    
    print("\n📊 Current Data:")
    for key, count in sorted(counts.items()):
        print(f"  {key}: {count}")
    
    total = sum(counts.values())
    print(f"\n  Total records to delete: {total}")
    
    return counts


def clean_everything(dry_run=True):
    """
    Delete ALL catalog data.
    
    Args:
        dry_run: If True, only show what would be done (don't actually clean)
    """
    counts = print_summary()
    
    total = sum(counts.values())
    if total == 0:
        print("\n✅ No data to clean - database is already empty!")
        return
    
    print("\n" + "=" * 80)
    print("CLEANUP PLAN")
    print("=" * 80)
    
    if dry_run:
        print("\n⚠️  DRY RUN MODE - No actual changes will be made\n")
        print("Would delete ALL catalog data:")
        print("  - All Products, Variants, Attribute Values")
        print("  - All ProductTypes, Attributes, AttributeValues")
        print("  - All Associations (ProductTypeAttribute, Axes, Listings)")
        print("  - Everything catalog-related")
    else:
        print("\n⚠️  ACTUAL CLEANUP MODE - This will delete ALL catalog data!\n")
        print("Will delete:")
        for key, count in sorted(counts.items()):
            if count > 0:
                print(f"  - {key}: {count} records")
    
    if not dry_run:
        print("\n" + "=" * 80)
        print("CLEANING DATA...")
        print("=" * 80)
        
        with transaction.atomic():
            # Delete in dependency order
            
            # Step 1: Delete ProductAttributeValue (references Product and Variant)
            deleted = ProductAttributeValue.objects.all().delete()
            print(f"  ✓ Deleted {deleted[0]} ProductAttributeValue records")
            
            # Step 2: Delete axes and listing data (references Product/Variant/Channel)
            deleted = ChannelListingAxis.objects.all().delete()
            print(f"  ✓ Deleted {deleted[0]} ChannelListingAxis records")
            
            deleted = ChannelListingMap.objects.all().delete()
            print(f"  ✓ Deleted {deleted[0]} ChannelListingMap records")
            
            deleted = ChannelListing.objects.all().delete()
            print(f"  ✓ Deleted {deleted[0]} ChannelListing records")
            
            deleted = ChannelVariantAxis.objects.all().delete()
            print(f"  ✓ Deleted {deleted[0]} ChannelVariantAxis records")
            
            deleted = ProductVariantAxis.objects.all().delete()
            print(f"  ✓ Deleted {deleted[0]} ProductVariantAxis records")
            
            # Step 3: Delete BundleComponent (references Variant - PROTECT)
            deleted = BundleComponent.objects.all().delete()
            print(f"  ✓ Deleted {deleted[0]} BundleComponent records")
            
            # Step 4: Delete Variants (references Product)
            deleted = Variant.objects.all().delete()
            print(f"  ✓ Deleted {deleted[0]} Variant records")
            
            # Step 5: Delete Products (references ProductType)
            deleted = Product.objects.all().delete()
            print(f"  ✓ Deleted {deleted[0]} Product records")
            
            # Step 6: Delete ProductTypeAttribute (references ProductType and Attribute)
            deleted = ProductTypeAttribute.objects.all().delete()
            print(f"  ✓ Deleted {deleted[0]} ProductTypeAttribute records")
            
            # Step 7: Delete AttributeMap first if it exists (references AttributeValue - PROTECT)
            if KW_AVAILABLE and AttributeMap:
                deleted = AttributeMap.objects.all().delete()
                print(f"  ✓ Deleted {deleted[0]} AttributeMap records")
            
            # Step 8: Delete AttributeMapping if it exists (references Attribute - PROTECT)
            if IMPORTER_AVAILABLE and AttributeMapping:
                deleted = AttributeMapping.objects.all().delete()
                print(f"  ✓ Deleted {deleted[0]} AttributeMapping records")
            
            # Step 9: Delete TemplatePart if it exists (references Attribute - PROTECT)
            if TEMPLATE_PART_AVAILABLE and TemplatePart:
                deleted = TemplatePart.objects.all().delete()
                print(f"  ✓ Deleted {deleted[0]} TemplatePart records")
            
            # Step 10: Delete AttributeValue (references Attribute)
            deleted = AttributeValue.objects.all().delete()
            print(f"  ✓ Deleted {deleted[0]} AttributeValue records")
            
            # Step 11: Delete Attributes
            deleted = Attribute.objects.all().delete()
            print(f"  ✓ Deleted {deleted[0]} Attribute records")
            
            # Step 12: Delete PlannerSeed if it exists (references ProductType - PROTECT)
            if PLANNER_SEED_AVAILABLE and PlannerSeed:
                deleted = PlannerSeed.objects.all().delete()
                print(f"  ✓ Deleted {deleted[0]} PlannerSeed records")
            
            # Step 13: Delete PlannerRun if it exists (references ProductType - PROTECT)
            if PLANNER_RUN_AVAILABLE and PlannerRun:
                deleted = PlannerRun.objects.all().delete()
                print(f"  ✓ Deleted {deleted[0]} PlannerRun records")
            
            # Step 14: Delete Template if it exists (references ProductType - PROTECT)
            if TEMPLATE_PART_AVAILABLE and Template:
                deleted = Template.objects.all().delete()
                print(f"  ✓ Deleted {deleted[0]} Template records")
            
            # Step 15: Delete ProductTypes
            deleted = ProductType.objects.all().delete()
            print(f"  ✓ Deleted {deleted[0]} ProductType records")
            
            print("\n✅ Complete cleanup finished!")
            
            # Verify
            print("\n" + "=" * 80)
            print("VERIFICATION")
            print("=" * 80)
            
            remaining_counts = {
                'Products': Product.objects.count(),
                'Variants': Variant.objects.count(),
                'ProductAttributeValue': ProductAttributeValue.objects.count(),
                'ProductType': ProductType.objects.count(),
                'Attribute': Attribute.objects.count(),
                'AttributeValue': AttributeValue.objects.count(),
                'ProductTypeAttribute': ProductTypeAttribute.objects.count(),
            }
            
            all_zero = True
            for key, count in sorted(remaining_counts.items()):
                status = "✅" if count == 0 else "⚠️"
                print(f"  {status} Remaining {key}: {count}")
                if count > 0:
                    all_zero = False
            
            if all_zero:
                print("\n✅ Database is completely clean and ready for fresh import!")
            else:
                print("\n⚠️  Warning: Some data still remains!")


if __name__ == "__main__":
    print("=" * 80)
    print("COMPLETE DATABASE CLEANUP SCRIPT")
    print("=" * 80)
    print("\n⚠️  WARNING: This will delete ALL catalog data!")
    print("   - Products, Variants, Attributes, ProductTypes")
    print("   - All associations and axes")
    print("   - Everything catalog-related")
    print("\n   This gives you a completely clean database.")
    
    # Run dry run first
    clean_everything(dry_run=True)
    
    print("\n" + "=" * 80)
    print("\nTo perform the actual cleanup:")
    print("  1. Review the summary above carefully")
    print("  2. Uncomment the line below, or")
    print("  3. Run in Django shell:")
    print("     >>> clean_everything(dry_run=False)")
    print("\n" + "=" * 80)
    
    # Uncomment to actually clean:
    # clean_everything(dry_run=False)
