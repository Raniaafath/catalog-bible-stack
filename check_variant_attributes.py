#!/usr/bin/env python3
"""
Script to check how attributes and values are linked to variants in the database.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from catalog.models import Variant, ProductAttributeValue, Attribute, AttributeValue, Product

def check_variant_attributes():
    # Find variants with "roucst" in their data
    print("=" * 80)
    print("SEARCHING FOR VARIANTS WITH 'roucst'")
    print("=" * 80)
    
    variants = Variant.objects.filter(
        source_title__icontains='roucst'
    ) | Variant.objects.filter(
        sku__icontains='roucst'
    ) | Variant.objects.filter(
        product__code__icontains='roucst'
    )
    
    if variants.count() == 0:
        print("\nNo variants found with 'roucst'. Checking recent variants...")
        variants = Variant.objects.all().order_by('-id')[:10]
        print(f"Showing last {variants.count()} variants instead:\n")
    
    for variant in variants:
        print(f"\n{'='*80}")
        print(f"VARIANT ID: {variant.id}")
        print(f"  SKU: {variant.sku}")
        print(f"  Barcode: {variant.barcode}")
        print(f"  Product: {variant.product.code} (ID: {variant.product.id})")
        print(f"  Source Title: {variant.source_title[:100] if variant.source_title else 'N/A'}")
        print(f"  Axis Signature: {variant.axis_signature}")
        
        # Get all attribute values for this variant
        attribute_values = ProductAttributeValue.objects.filter(variant=variant).select_related('attribute', 'attribute_value')
        
        print(f"\n  ATTRIBUTES LINKED TO THIS VARIANT: {attribute_values.count()}")
        print(f"  {'-'*76}")
        
        if attribute_values.count() == 0:
            print("  ⚠️  No attributes linked to this variant!")
        else:
            for pav in attribute_values:
                attr = pav.attribute
                print(f"\n  Attribute: {attr.code} (ID: {attr.id}, Type: {attr.data_type})")
                
                # Check what type of value is stored
                if pav.attribute_value:
                    print(f"    → Value (Enum): {pav.attribute_value.code} (ID: {pav.attribute_value.id})")
                elif pav.value_text:
                    print(f"    → Value (Text): {pav.value_text}")
                elif pav.value_number is not None:
                    print(f"    → Value (Number): {pav.value_number}")
                elif pav.value_bool is not None:
                    print(f"    → Value (Boolean): {pav.value_bool}")
                elif pav.value_json:
                    print(f"    → Value (JSON): {pav.value_json}")
                
                if pav.unit:
                    print(f"    → Unit: {pav.unit}")
                if pav.is_axis:
                    print(f"    → Is Axis: {pav.is_axis}")
        
        # Also check product-level attributes
        product_attrs = ProductAttributeValue.objects.filter(product=variant.product, variant__isnull=True)
        if product_attrs.exists():
            print(f"\n  PRODUCT-LEVEL ATTRIBUTES (shared across variants): {product_attrs.count()}")
            for pav in product_attrs[:5]:  # Show first 5
                print(f"    - {pav.attribute.code}: ", end="")
                if pav.attribute_value:
                    print(f"{pav.attribute_value.code}")
                elif pav.value_text:
                    print(f"{pav.value_text}")
                elif pav.value_number is not None:
                    print(f"{pav.value_number}")
    
    print(f"\n{'='*80}")
    print("SUMMARY")
    print("=" * 80)
    
    # Overall statistics
    total_variants = Variant.objects.count()
    variants_with_attrs = ProductAttributeValue.objects.filter(variant__isnull=False).values('variant').distinct().count()
    total_variant_attrs = ProductAttributeValue.objects.filter(variant__isnull=False).count()
    
    print(f"Total variants in database: {total_variants}")
    print(f"Variants with attributes: {variants_with_attrs}")
    print(f"Total variant-level attribute values: {total_variant_attrs}")
    
    # Check attribute distribution
    print(f"\nAttribute distribution (top 10):")
    from django.db.models import Count
    attr_counts = ProductAttributeValue.objects.filter(variant__isnull=False).values('attribute__code').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    for item in attr_counts:
        print(f"  {item['attribute__code']}: {item['count']} values")

if __name__ == '__main__':
    check_variant_attributes()
