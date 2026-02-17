"""
Example script demonstrating the manual grouping workflow.

This script shows how to:
1. Create variants with attributes
2. Compare variants to find differences
3. Group variants under a product with variation axes

Run from Django shell:
    python manage.py shell < docs/examples/manual_grouping_example.py

Or interactively:
    python manage.py shell
    >>> exec(open('docs/examples/manual_grouping_example.py').read())
"""

from django.db import transaction
from catalog.models import (
    Product, ProductType, Variant, Attribute, AttributeValue,
    ProductAttributeValue
)
from catalog.services.variant_grouping import compare_variants, group_variants_with_axes
from pub.models import Channel

print("\n" + "="*60)
print("MANUAL GROUPING WORKFLOW - EXAMPLE")
print("="*60 + "\n")

# Clean up from previous runs
print("Step 0: Cleanup from previous runs...")
Variant.objects.filter(sku__startswith='DEMO-BIKE-').delete()
Product.objects.filter(code__startswith='demo-').delete()

# Setup: Create product type
print("\nStep 1: Setup - Create Product Type (Category)")
product_type, created = ProductType.objects.get_or_create(
    code='bikes',
    defaults={'default_label': 'Bikes'}
)
print(f"  ✓ Product type: {product_type.code} (created: {created})")

# Setup: Create attributes
print("\nStep 2: Setup - Create Attributes")
color_attr, _ = Attribute.objects.get_or_create(
    code='color',
    defaults={'data_type': 'enum'}
)
print(f"  ✓ Attribute: {color_attr.code}")

size_attr, _ = Attribute.objects.get_or_create(
    code='size',
    defaults={'data_type': 'enum'}
)
print(f"  ✓ Attribute: {size_attr.code}")

material_attr, _ = Attribute.objects.get_or_create(
    code='material',
    defaults={'data_type': 'text'}
)
print(f"  ✓ Attribute: {material_attr.code}")

# Create attribute values (enum values)
color_red, _ = AttributeValue.objects.get_or_create(
    attribute=color_attr, code='red'
)
color_blue, _ = AttributeValue.objects.get_or_create(
    attribute=color_attr, code='blue'
)
size_medium, _ = AttributeValue.objects.get_or_create(
    attribute=size_attr, code='medium'
)
size_large, _ = AttributeValue.objects.get_or_create(
    attribute=size_attr, code='large'
)
size_xl, _ = AttributeValue.objects.get_or_create(
    attribute=size_attr, code='xl'
)

# Setup: Create channel
print("\nStep 3: Setup - Create Channel")
channel, created = Channel.objects.get_or_create(
    code='shopify',
    defaults={'name': 'Shopify'}
)
print(f"  ✓ Channel: {channel.name} (created: {created})")

# Step 4: Create placeholder products (simulating import with group_by_product_key=False)
print("\nStep 4: Create Variants (simulating import with standalone mode)")
print("  Each variant gets its own placeholder product (1:1 ratio)")

variants_data = [
    ('DEMO-BIKE-RED-M', 'red', 'medium', 'aluminum'),
    ('DEMO-BIKE-RED-L', 'red', 'large', 'aluminum'),
    ('DEMO-BIKE-BLUE-M', 'blue', 'medium', 'aluminum'),
    ('DEMO-BIKE-BLUE-L', 'blue', 'large', 'aluminum'),
    ('DEMO-BIKE-BLUE-XL', 'blue', 'xl', 'aluminum'),
]

variants = []
with transaction.atomic():
    for sku, color, size, material in variants_data:
        # Create placeholder product (1:1 with variant)
        product = Product.objects.create(
            code=f'demo-{sku.lower()}',
            product_type=product_type,
            status=Product.Status.DRAFT,
        )
        
        # Create variant
        variant = Variant.objects.create(
            product=product,
            sku=sku,
            source_title=f"Mountain Bike {color.title()} {size.title()}",
        )
        
        # Add attributes to variant
        # Color
        ProductAttributeValue.objects.create(
            variant=variant,
            attribute=color_attr,
            attribute_value=color_red if color == 'red' else color_blue,
        )
        
        # Size
        size_val = {'medium': size_medium, 'large': size_large, 'xl': size_xl}[size]
        ProductAttributeValue.objects.create(
            variant=variant,
            attribute=size_attr,
            attribute_value=size_val,
        )
        
        # Material
        ProductAttributeValue.objects.create(
            variant=variant,
            attribute=material_attr,
            value_text=material,
        )
        
        variants.append(variant)
        print(f"  ✓ Created variant: {sku} (product: {product.code})")

variant_ids = [v.id for v in variants]
print(f"\n  Total: {len(variants)} variants created (each with own product)")

# Step 5: Compare variants
print("\nStep 5: Compare Variants to Find Differences")
print(f"  Comparing variant IDs: {variant_ids}")

comparison = compare_variants(variant_ids)

print(f"\n  Variants compared: {len(comparison['variants'])}")
print(f"\n  DIFFERENCES DETECTED:")
for diff in comparison['differences']:
    print(f"    • {diff['attribute_code']}: {diff['unique_values_count']} unique values")
    print(f"      Values: {', '.join(diff['unique_values'])}")
    if diff['is_candidate_axis']:
        print(f"      ✓ RECOMMENDED as variation axis")
    print()

print(f"  COMMON ATTRIBUTES:")
for common in comparison['common_attributes']:
    print(f"    • {common['attribute_code']}: {common['common_value']} (same for all)")

# Step 6: Group variants with axes
print("\nStep 6: Group Variants with Variation Axes")
print(f"  Channel: {channel.code}")
print(f"  Axes: color (position 0), size (position 1)")

result = group_variants_with_axes(
    variant_ids=variant_ids,
    channel_id=channel.id,
    variation_axes=[
        {'attribute_id': color_attr.id, 'position': 0},
        {'attribute_id': size_attr.id, 'position': 1},
    ],
    create_new_product=True,
    product_code='demo-mountain-bike',
    product_type_id=product_type.id,
)

print(f"\n  ✓ Product created: {result['product']['code']} (ID: {result['product']['id']})")
print(f"  ✓ Variants grouped: {result['variants_grouped']}")
print(f"  ✓ Variation axes set:")
for axis in result['axes']:
    print(f"    - {axis['attribute_code']} (position {axis['position']})")

# Verify results
print("\nStep 7: Verify Results")
grouped_product = Product.objects.get(code='demo-mountain-bike')
grouped_variants = Variant.objects.filter(product=grouped_product)

print(f"  Product: {grouped_product.code}")
print(f"  Variants in group: {grouped_variants.count()}")
for v in grouped_variants:
    print(f"    • {v.sku}")

from catalog.models import ChannelVariantAxis
axes = ChannelVariantAxis.objects.filter(
    product=grouped_product,
    channel=channel
).order_by('position')

print(f"\n  Variation axes for {channel.code}:")
for axis in axes:
    print(f"    {axis.position + 1}. {axis.attribute.code}")

print("\n" + "="*60)
print("EXAMPLE COMPLETE!")
print("="*60)
print("\nWhat happened:")
print("1. Created 5 variants (each with placeholder product)")
print("2. Compared variants → Found differences in color & size")
print("3. Grouped variants → Created 1 product with 5 variants")
print("4. Set variation axes → color, size for Shopify")
print("\nNext steps:")
print("- Add more channels with different axes")
print("- Generate titles using variation axes")
print("- Export to marketplace")
print("\nCleanup:")
print("  To remove demo data:")
print("    Variant.objects.filter(sku__startswith='DEMO-BIKE-').delete()")
print("    Product.objects.filter(code__startswith='demo-').delete()")
print()
