#!/usr/bin/env python
"""Quick script to check current database state"""
from catalog.models import Product, Variant, ProductVariantAxis, ProductAttributeValue
from pub.models import Channel
from django.db.models import Count

print('=== PRODUCTS ===')
total_products = Product.objects.count()
print(f'Total products: {total_products}')
products_with_variants = Product.objects.annotate(vc=Count('variants')).filter(vc__gt=1).count()
print(f'Products with multiple variants: {products_with_variants}')
products_with_axes = ProductVariantAxis.objects.values('product').distinct().count()
print(f'Products with axes defined: {products_with_axes}')

print('\n=== VARIANTS ===')
total_variants = Variant.objects.count()
print(f'Total variants: {total_variants}')
if total_products > 0:
    print(f'Variants per product (avg): {total_variants / total_products:.2f}')

print('\n=== CHANNELS ===')
total_channels = Channel.objects.count()
print(f'Total channels: {total_channels}')
for c in Channel.objects.all()[:10]:
    print(f'  - {c.code} (id={c.id}, active={c.is_active})')

print('\n=== AXES ===')
total_axes = ProductVariantAxis.objects.count()
print(f'Total ProductVariantAxis records: {total_axes}')
if total_axes > 0:
    print('Sample axes:')
    for axis in ProductVariantAxis.objects.select_related('product', 'attribute')[:5]:
        print(f'  - Product {axis.product.code} → {axis.attribute.code} (position={axis.position})')

print('\n=== ATTRIBUTE VALUES ===')
total_pav = ProductAttributeValue.objects.count()
print(f'Total ProductAttributeValue: {total_pav}')
product_level = ProductAttributeValue.objects.filter(product__isnull=False).count()
variant_level = ProductAttributeValue.objects.filter(variant__isnull=False).count()
print(f'  - Product-level: {product_level}')
print(f'  - Variant-level: {variant_level}')
