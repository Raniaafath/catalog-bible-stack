"""
Example: How to Use Parent-Variant Import with Variation Axes

This file demonstrates the complete workflow for importing products with variants
and generating titles based on variation axes.
"""

# ==============================================================================
# STEP 1: Prepare Your CSV File
# ==============================================================================

# Example CSV content:
csv_content = """
parent_id,sku,category,brand,title,color,size,material,price,barcode
BIKE-001,BIKE-001-RED-M,Bikes,Trek,Mountain Bike Pro,Red,Medium,Aluminum,599.99,123456001
BIKE-001,BIKE-001-RED-L,Bikes,Trek,Mountain Bike Pro,Red,Large,Aluminum,649.99,123456002
BIKE-001,BIKE-001-BLUE-M,Bikes,Trek,Mountain Bike Pro,Blue,Medium,Aluminum,599.99,123456003
BIKE-001,BIKE-001-BLUE-L,Bikes,Trek,Mountain Bike Pro,Blue,Large,Aluminum,649.99,123456004
PHONE-001,PHONE-001-BLK-64,Phones,Samsung,Galaxy S24,Black,64GB,Glass,799.99,789012001
PHONE-001,PHONE-001-BLK-128,Phones,Samsung,Galaxy S24,Black,128GB,Glass,899.99,789012002
PHONE-001,PHONE-001-WHT-64,Phones,Samsung,Galaxy S24,White,64GB,Glass,799.99,789012003
PHONE-001,PHONE-001-WHT-128,Phones,Samsung,Galaxy S24,White,128GB,Glass,899.99,789012004
"""

# Save this as products.csv

# ==============================================================================
# STEP 2: Upload and Parse the File
# ==============================================================================

from django.core.files.base import ContentFile
from importer.models import ProductImport
from importer.services import parse_import

# Create import record
import_obj = ProductImport.objects.create(
    created_by='admin',
    source_file=ContentFile(csv_content.encode(), name='products.csv'),
    original_filename='products.csv',
    file_type='csv',
    status=ProductImport.Status.UPLOADED
)

# Parse the file
parse_result = parse_import(import_obj.id)
print(f"Parsed {parse_result.total} rows: {parse_result.ok} OK, {parse_result.errors} errors")

# ==============================================================================
# STEP 3: Review and Configure Column Mappings (Optional)
# ==============================================================================

from importer.models import ImportColumnRule

# View auto-detected column rules
rules = ImportColumnRule.objects.filter(product_import=import_obj)
print("\nAuto-detected column mappings:")
for rule in rules:
    print(f"  {rule.column_name:20} -> {rule.role}")

# The system should auto-detect:
# - parent_id -> PRODUCT_KEY
# - sku -> VARIANT_KEY
# - category -> CATEGORY
# - brand -> BRAND
# - title -> TITLE
# - color, size, material, price -> ATTRIBUTE

# ==============================================================================
# STEP 4: Mark Variation Axes (Optional but Recommended)
# ==============================================================================

# Explicitly mark which attributes are variation axes
color_rule = ImportColumnRule.objects.get(product_import=import_obj, column_name='color')
color_rule.is_variation_axis = True
color_rule.axis_priority = 0  # First axis (most important)
color_rule.variant_level = True  # Store at variant level
color_rule.save()

size_rule = ImportColumnRule.objects.get(product_import=import_obj, column_name='size')
size_rule.is_variation_axis = True
size_rule.axis_priority = 1  # Second axis
size_rule.variant_level = True
size_rule.save()

# Mark price as variant-level (not an axis, but varies per variant)
price_rule = ImportColumnRule.objects.get(product_import=import_obj, column_name='price')
price_rule.variant_level = True
price_rule.save()

# Material is product-level (same for all variants) - no changes needed

print("\nConfigured variation axes:")
print(f"  Axis 0: color")
print(f"  Axis 1: size")

# ==============================================================================
# STEP 5: Process the Import
# ==============================================================================

from importer.services import process_import

stats = process_import(import_obj.id)

print(f"\nImport processing complete:")
print(f"  Products created: {stats['products_created']}")
print(f"  Variants created: {stats['variants_created']}")
print(f"  Variation axes detected: {stats['variation_axes_detected']}")
print(f"  Attribute values created: {stats['attribute_values_created']}")
print(f"  Errors: {stats['errors']}")

# Expected output:
# Products created: 2 (BIKE-001, PHONE-001)
# Variants created: 8 (4 bikes + 4 phones)
# Variation axes detected: 4 (2 per product)

# ==============================================================================
# STEP 6: Verify the Data
# ==============================================================================

from catalog.models import Product, Variant, ProductVariantAxis

# Check created products
bike_product = Product.objects.get(code='bike-001')
print(f"\nProduct: {bike_product.code}")
print(f"  Brand: {bike_product.brand}")
print(f"  Title: {bike_product.default_label or bike_product.source_title}")
print(f"  Variants: {bike_product.variants.count()}")

# Check variation axes
axes = ProductVariantAxis.objects.filter(product=bike_product).order_by('position')
print(f"  Variation axes:")
for axis in axes:
    print(f"    {axis.position}: {axis.attribute.code}")

# Check variants
print(f"  Variant details:")
for variant in bike_product.variants.all():
    print(f"    {variant.sku}")
    print(f"      Signature: {variant.axis_signature}")
    print(f"      Barcode: {variant.barcode}")
    
    # Show axis values
    for axis in axes:
        pav = variant.attribute_values.filter(attribute=axis.attribute, is_axis=True).first()
        if pav:
            value = pav.attribute_value.code if pav.attribute_value else pav.value_text
            print(f"      {axis.attribute.code}: {value}")

# ==============================================================================
# STEP 7: Generate Variant Titles
# ==============================================================================

from catalog.services import generate_variant_title, generate_all_variant_titles

# Generate title for a single variant
variant = bike_product.variants.first()
title = generate_variant_title(variant)
print(f"\nGenerated title: {title}")
# Expected: "Mountain Bike Pro - Red Medium"

# Generate titles for all variants of the product
all_titles = generate_all_variant_titles(bike_product)
print(f"\nAll variant titles:")
for sku, title in all_titles.items():
    print(f"  {sku}: {title}")

# Expected output:
#   BIKE-001-RED-M: Mountain Bike Pro - Red Medium
#   BIKE-001-RED-L: Mountain Bike Pro - Red Large
#   BIKE-001-BLUE-M: Mountain Bike Pro - Blue Medium
#   BIKE-001-BLUE-L: Mountain Bike Pro - Blue Large

# ==============================================================================
# STEP 8: Use Custom Title Templates
# ==============================================================================

from catalog.services import generate_variant_title_template

# Create a custom template
template_generator = generate_variant_title_template(
    bike_product,
    template="{base_title} in {color} ({size})"
)

print(f"\nCustom template titles:")
for variant in bike_product.variants.all():
    custom_title = template_generator(variant)
    print(f"  {variant.sku}: {custom_title}")

# Expected output:
#   BIKE-001-RED-M: Mountain Bike Pro in Red (Medium)
#   BIKE-001-RED-L: Mountain Bike Pro in Red (Large)
#   etc.

# ==============================================================================
# STEP 9: Query Variants by Axis Values
# ==============================================================================

from catalog.models import ProductAttributeValue

# Find all Red bikes
red_variants = Variant.objects.filter(
    product=bike_product,
    attribute_values__attribute__code='color',
    attribute_values__attribute_value__code='red'
)

print(f"\nRed bike variants:")
for variant in red_variants:
    print(f"  {variant.sku}")

# Find all Large bikes
large_variants = Variant.objects.filter(
    product=bike_product,
    attribute_values__attribute__code='size',
    attribute_values__attribute_value__code='large'
)

print(f"\nLarge bike variants:")
for variant in large_variants:
    print(f"  {variant.sku}")

# ==============================================================================
# STEP 10: Get Axis Value Combinations
# ==============================================================================

from catalog.services import get_axis_value_combinations

# Get all possible axis combinations for the product
combinations = get_axis_value_combinations(bike_product)
print(f"\nAll axis combinations for {bike_product.code}:")
for combo in combinations:
    print(f"  {combo}")

# Expected output:
#   {'color': 'blue', 'size': 'large'}
#   {'color': 'blue', 'size': 'medium'}
#   {'color': 'red', 'size': 'large'}
#   {'color': 'red', 'size': 'medium'}

# ==============================================================================
# COMPLETE WORKFLOW SUMMARY
# ==============================================================================

print("\n" + "="*80)
print("WORKFLOW SUMMARY")
print("="*80)

print(f"""
1. ✓ Uploaded CSV with {parse_result.total} rows
2. ✓ Auto-detected column mappings
3. ✓ Configured variation axes (color, size)
4. ✓ Created {stats['products_created']} products
5. ✓ Created {stats['variants_created']} variants
6. ✓ Detected {stats['variation_axes_detected']} variation axes
7. ✓ Generated variant titles using axes
8. ✓ Ready for title generation in production

Next Steps:
- Integrate title generation into your product catalog API
- Use variation axes in frontend filters and navigation
- Generate SEO-friendly URLs using axis values
- Create variant selection UI based on axes
""")

# ==============================================================================
# INTEGRATION WITH FRONTEND/API
# ==============================================================================

# Example API endpoint to get product with variants and titles:
"""
from rest_framework import serializers, viewsets
from catalog.models import Product, Variant
from catalog.services import generate_variant_title

class VariantSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    axis_values = serializers.SerializerMethodField()
    
    def get_title(self, obj):
        return generate_variant_title(obj)
    
    def get_axis_values(self, obj):
        from catalog.services import get_variant_axis_values
        return get_variant_axis_values(obj)
    
    class Meta:
        model = Variant
        fields = ['sku', 'title', 'barcode', 'axis_signature', 'axis_values']

class ProductDetailSerializer(serializers.ModelSerializer):
    variants = VariantSerializer(many=True, read_only=True)
    variation_axes = serializers.SerializerMethodField()
    
    def get_variation_axes(self, obj):
        axes = obj.variant_axes.order_by('position')
        return [
            {
                'code': axis.attribute.code,
                'position': axis.position,
                'label': axis.label_override or axis.attribute.code.title()
            }
            for axis in axes
        ]
    
    class Meta:
        model = Product
        fields = ['code', 'brand', 'title', 'variation_axes', 'variants']

# API Response Example:
{
    "code": "bike-001",
    "brand": "Trek",
    "title": "Mountain Bike Pro",
    "variation_axes": [
        {"code": "color", "position": 0, "label": "Color"},
        {"code": "size", "position": 1, "label": "Size"}
    ],
    "variants": [
        {
            "sku": "BIKE-001-RED-M",
            "title": "Mountain Bike Pro - Red Medium",
            "barcode": "123456001",
            "axis_signature": "red:medium",
            "axis_values": {"color": "red", "size": "medium"}
        },
        {
            "sku": "BIKE-001-RED-L",
            "title": "Mountain Bike Pro - Red Large",
            "barcode": "123456002",
            "axis_signature": "red:large",
            "axis_values": {"color": "red", "size": "large"}
        }
    ]
}
"""
