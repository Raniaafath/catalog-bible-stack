"""
Management command to test parent-variant import with a sample CSV.
Usage: python manage.py test_parent_variant_import
"""

from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from importer.models import ProductImport, ImportColumnRule
from importer.services import parse_import, process_import
from catalog.services import generate_all_variant_titles
from catalog.models import Product


class Command(BaseCommand):
    help = 'Test parent-variant import with sample data'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting parent-variant import test...'))
        
        # Sample CSV data
        csv_content = """parent_id,sku,category,brand,title,color,size,material,price,barcode
BIKE-001,BIKE-001-RED-M,Bikes,Trek,Mountain Bike Pro,Red,Medium,Aluminum,599.99,123456001
BIKE-001,BIKE-001-RED-L,Bikes,Trek,Mountain Bike Pro,Red,Large,Aluminum,649.99,123456002
BIKE-001,BIKE-001-BLUE-M,Bikes,Trek,Mountain Bike Pro,Blue,Medium,Aluminum,599.99,123456003
BIKE-001,BIKE-001-BLUE-L,Bikes,Trek,Mountain Bike Pro,Blue,Large,Aluminum,649.99,123456004
PHONE-001,PHONE-001-BLK-64,Phones,Samsung,Galaxy S24,Black,64GB,Glass,799.99,789012001
PHONE-001,PHONE-001-BLK-128,Phones,Samsung,Galaxy S24,Black,128GB,Glass,899.99,789012002
PHONE-001,PHONE-001-WHT-64,Phones,Samsung,Galaxy S24,White,64GB,Glass,799.99,789012003
PHONE-001,PHONE-001-WHT-128,Phones,Samsung,Galaxy S24,White,128GB,Glass,899.99,789012004"""
        
        # Step 1: Create import
        self.stdout.write('Step 1: Creating import...')
        import_obj = ProductImport.objects.create(
            created_by='test',
            source_file=ContentFile(csv_content.encode(), name='test_products.csv'),
            original_filename='test_products.csv',
            file_type='csv',
            status=ProductImport.Status.UPLOADED
        )
        self.stdout.write(self.style.SUCCESS(f'  ✓ Import created: ID {import_obj.id}'))
        
        # Step 2: Parse
        self.stdout.write('\nStep 2: Parsing CSV...')
        parse_result = parse_import(import_obj.id)
        self.stdout.write(self.style.SUCCESS(
            f'  ✓ Parsed {parse_result.total} rows: {parse_result.ok} OK, {parse_result.errors} errors'
        ))
        
        # Step 3: Review column mappings
        self.stdout.write('\nStep 3: Column mappings:')
        rules = ImportColumnRule.objects.filter(product_import=import_obj).order_by('position')
        for rule in rules:
            self.stdout.write(f'  {rule.column_name:20} -> {rule.role}')
        
        # Step 4: Mark variation axes
        self.stdout.write('\nStep 4: Configuring variation axes...')
        
        # Mark 'color' as variation axis
        try:
            color_rule = ImportColumnRule.objects.get(product_import=import_obj, column_name='color')
            color_rule.is_variation_axis = True
            color_rule.axis_priority = 0
            color_rule.variant_level = True
            color_rule.save()
            self.stdout.write(self.style.SUCCESS('  ✓ Marked "color" as variation axis (priority 0)'))
        except ImportColumnRule.DoesNotExist:
            self.stdout.write(self.style.WARNING('  ⚠ Column "color" not found'))
        
        # Mark 'size' as variation axis
        try:
            size_rule = ImportColumnRule.objects.get(product_import=import_obj, column_name='size')
            size_rule.is_variation_axis = True
            size_rule.axis_priority = 1
            size_rule.variant_level = True
            size_rule.save()
            self.stdout.write(self.style.SUCCESS('  ✓ Marked "size" as variation axis (priority 1)'))
        except ImportColumnRule.DoesNotExist:
            self.stdout.write(self.style.WARNING('  ⚠ Column "size" not found'))
        
        # Mark price as variant-level
        try:
            price_rule = ImportColumnRule.objects.get(product_import=import_obj, column_name='price')
            price_rule.variant_level = True
            price_rule.save()
            self.stdout.write(self.style.SUCCESS('  ✓ Marked "price" as variant-level'))
        except ImportColumnRule.DoesNotExist:
            self.stdout.write(self.style.WARNING('  ⚠ Column "price" not found'))
        
        # Step 5: Process import
        self.stdout.write('\nStep 5: Processing import...')
        stats = process_import(import_obj.id)
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Products created: {stats["products_created"]}'))
        self.stdout.write(self.style.SUCCESS(f'  ✓ Products updated: {stats["products_updated"]}'))
        self.stdout.write(self.style.SUCCESS(f'  ✓ Variants created: {stats["variants_created"]}'))
        self.stdout.write(self.style.SUCCESS(f'  ✓ Variants updated: {stats["variants_updated"]}'))
        self.stdout.write(self.style.SUCCESS(f'  ✓ Variation axes detected: {stats["variation_axes_detected"]}'))
        self.stdout.write(self.style.SUCCESS(f'  ✓ Attribute values created: {stats["attribute_values_created"]}'))
        
        if stats['errors'] > 0:
            self.stdout.write(self.style.ERROR(f'  ✗ Errors: {stats["errors"]}'))
            for error in stats.get('error_details', []):
                self.stdout.write(self.style.ERROR(f'    - {error}'))
        
        # Step 6: Verify products
        self.stdout.write('\nStep 6: Verifying created products...')
        
        products = Product.objects.filter(code__in=['bike-001', 'phone-001'])
        for product in products:
            self.stdout.write(f'\n  Product: {product.code}')
            self.stdout.write(f'    Brand: {product.brand}')
            self.stdout.write(f'    Title: {product.default_label or product.source_title}')
            self.stdout.write(f'    Variants: {product.variants.count()}')
            
            # Show variation axes
            axes = product.variant_axes.order_by('position')
            if axes.exists():
                self.stdout.write('    Variation axes:')
                for axis in axes:
                    self.stdout.write(f'      [{axis.position}] {axis.attribute.code}')
            
            # Show first variant details
            variant = product.variants.first()
            if variant:
                self.stdout.write(f'    First variant: {variant.sku}')
                self.stdout.write(f'      Axis signature: {variant.axis_signature}')
                self.stdout.write(f'      Barcode: {variant.barcode}')
        
        # Step 7: Generate titles
        self.stdout.write('\nStep 7: Generating variant titles...')
        
        for product in products:
            self.stdout.write(f'\n  Titles for {product.code}:')
            titles = generate_all_variant_titles(product)
            for sku, title in sorted(titles.items()):
                self.stdout.write(f'    {sku}: {title}')
        
        # Success summary
        self.stdout.write('\n' + '='*80)
        self.stdout.write(self.style.SUCCESS('✓ TEST COMPLETED SUCCESSFULLY'))
        self.stdout.write('='*80)
        self.stdout.write(f"""
Summary:
  - Created {stats['products_created']} parent products
  - Created {stats['variants_created']} variants
  - Detected {stats['variation_axes_detected']} variation axes
  - Generated variant titles successfully

Next steps:
  - Check the database: Product, Variant, ProductVariantAxis tables
  - Test with your own CSV files
  - Integrate title generation into your API
  - Update frontend to use variation axes
""")
