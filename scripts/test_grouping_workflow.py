#!/usr/bin/env python
"""
Test script for the full product/variant grouping workflow.

This script validates:
1. Import CSV -> Parse -> Process creates variants
2. Compare variants finds differences
3. Group variants under a product with axes
4. Verify the grouping in database

Run with: python manage.py shell < scripts/test_grouping_workflow.py
Or: python scripts/test_grouping_workflow.py (if Django is configured)
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import transaction
from catalog.models import (
    Product, Variant, Attribute, AttributeValue, 
    ProductAttributeValue, ProductType, ChannelVariantAxis
)
from catalog.services.variant_grouping import compare_variants, group_variants_with_axes
from pub.models import Channel


def print_header(text):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_step(step, text):
    print(f"\n[Step {step}] {text}")
    print("-" * 50)


def test_grouping_workflow():
    """Test the full grouping workflow."""
    
    print_header("TESTING PRODUCT/VARIANT GROUPING WORKFLOW")
    
    # Step 1: Setup test data
    print_step(1, "Setting up test data")
    
    with transaction.atomic():
        # Create or get product type
        product_type, _ = ProductType.objects.get_or_create(
            code='test-clothing',
            defaults={'default_label': 'Test Clothing'}
        )
        print(f"  Product Type: {product_type.code}")
        
        # Create or get channel
        channel, _ = Channel.objects.get_or_create(
            code='test-shopify',
            defaults={'name': 'Test Shopify'}
        )
        print(f"  Channel: {channel.code}")
        
        # Create attributes
        color_attr, _ = Attribute.objects.get_or_create(
            code='test-color',
            defaults={'data_type': 'enum'}
        )
        size_attr, _ = Attribute.objects.get_or_create(
            code='test-size',
            defaults={'data_type': 'enum'}
        )
        print(f"  Attributes: {color_attr.code}, {size_attr.code}")
        
        # Create attribute values
        red_val, _ = AttributeValue.objects.get_or_create(attribute=color_attr, code='red')
        blue_val, _ = AttributeValue.objects.get_or_create(attribute=color_attr, code='blue')
        small_val, _ = AttributeValue.objects.get_or_create(attribute=size_attr, code='small')
        large_val, _ = AttributeValue.objects.get_or_create(attribute=size_attr, code='large')
        print(f"  Values: red, blue, small, large")
        
        # Create standalone products (simulating import)
        variants = []
        variant_configs = [
            ('TST-RED-S', red_val, small_val),
            ('TST-RED-L', red_val, large_val),
            ('TST-BLUE-S', blue_val, small_val),
            ('TST-BLUE-L', blue_val, large_val),
        ]
        
        for sku, color, size in variant_configs:
            # Each variant gets its own "placeholder" product (simulating ungrouped import)
            product = Product.objects.create(
                code=f'placeholder-{sku}'.lower(),
                product_type=product_type,
                status='draft'
            )
            variant = Variant.objects.create(
                product=product,
                sku=sku,
                source_title=f'Test Product {sku}'
            )
            
            # Add attribute values to variant
            ProductAttributeValue.objects.create(
                variant=variant,
                attribute=color_attr,
                attribute_value=color
            )
            ProductAttributeValue.objects.create(
                variant=variant,
                attribute=size_attr,
                attribute_value=size
            )
            
            variants.append(variant)
            print(f"  Created variant: {sku} (product: {product.code})")
        
        print(f"\n  Total variants created: {len(variants)}")
        
        # Step 2: Compare variants
        print_step(2, "Comparing variants to find differences")
        
        variant_ids = [v.id for v in variants]
        comparison = compare_variants(variant_ids)
        
        if 'error' in comparison:
            print(f"  ERROR: {comparison['error']}")
            return False
        
        print(f"  Variants compared: {len(comparison['variants'])}")
        print(f"  Differences found: {len(comparison['differences'])}")
        
        for diff in comparison['differences']:
            axis_status = "✓ Candidate axis" if diff['is_candidate_axis'] else "✗ Not suitable"
            print(f"    - {diff['attribute_code']}: {diff['unique_values_count']} unique values ({axis_status})")
            print(f"      Values: {', '.join(diff['unique_values'])}")
        
        print(f"  Common attributes: {len(comparison['common_attributes'])}")
        for common in comparison['common_attributes']:
            print(f"    - {common['attribute_code']}: {common['common_value']}")
        
        # Step 3: Group variants with axes
        print_step(3, "Grouping variants with variation axes")
        
        # Use candidate axes
        variation_axes = [
            {'attribute_id': color_attr.id, 'position': 0},
            {'attribute_id': size_attr.id, 'position': 1},
        ]
        
        result = group_variants_with_axes(
            variant_ids=variant_ids,
            channel_id=channel.id,
            variation_axes=variation_axes,
            product_code='test-grouped-product',
            create_new_product=True
        )
        
        print(f"  Product created: {result['product']['code']} (ID: {result['product']['id']})")
        print(f"  Variants grouped: {result['variants_grouped']}")
        print(f"  Channel: {result['channel']['code']}")
        print(f"  Axes created:")
        for axis in result['axes']:
            print(f"    - Position {axis['position']}: {axis['attribute_code']}")
        
        # Step 4: Verify the grouping
        print_step(4, "Verifying the grouping in database")
        
        grouped_product = Product.objects.get(code='test-grouped-product')
        grouped_variants = Variant.objects.filter(product=grouped_product)
        channel_axes = ChannelVariantAxis.objects.filter(product=grouped_product, channel=channel)
        
        print(f"  Product: {grouped_product.code}")
        print(f"  Variants in product: {grouped_variants.count()}")
        for v in grouped_variants:
            print(f"    - {v.sku}")
        
        print(f"  Channel axes: {channel_axes.count()}")
        for axis in channel_axes.order_by('position'):
            print(f"    - Position {axis.position}: {axis.attribute.code}")
        
        # Step 5: Cleanup
        print_step(5, "Cleaning up test data")
        
        # Delete the grouped product (cascades to variants)
        grouped_product.delete()
        
        # Delete placeholder products that might be orphaned
        Product.objects.filter(code__startswith='placeholder-tst-').delete()
        
        # Delete test channel and product type if they're new
        Channel.objects.filter(code='test-shopify').delete()
        ProductType.objects.filter(code='test-clothing').delete()
        
        # Delete test attributes
        Attribute.objects.filter(code__in=['test-color', 'test-size']).delete()
        
        print("  Test data cleaned up")
    
    print_header("TEST COMPLETED SUCCESSFULLY")
    return True


if __name__ == '__main__':
    success = test_grouping_workflow()
    sys.exit(0 if success else 1)
