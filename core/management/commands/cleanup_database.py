"""
Comprehensive database cleanup and organization command.

This command:
1. Identifies orphaned records (broken foreign keys)
2. Validates data integrity
3. Removes invalid/inconsistent data
4. Fixes common issues
5. Provides detailed reporting

Usage:
    python manage.py cleanup_database --dry-run  # Preview changes
    python manage.py cleanup_database              # Execute cleanup
    python manage.py cleanup_database --fix        # Auto-fix issues where possible
"""
from django.core.management.base import BaseCommand
from django.db import transaction, models
from django.db.models import Q, Count
from collections import defaultdict


class Command(BaseCommand):
    help = "Clean and organize database structure - identifies and fixes issues"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without making them',
        )
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Automatically fix issues where possible',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed information',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        auto_fix = options['fix']
        verbose = options['verbose']

        if dry_run:
            self.stdout.write(self.style.WARNING('\n🔍 DRY RUN MODE - No changes will be made\n'))
        else:
            self.stdout.write(self.style.WARNING('\n⚠️  LIVE MODE - Changes will be made\n'))

        issues = self.analyze_database(verbose)
        self.report_issues(issues, verbose)

        if not dry_run and auto_fix:
            self.fix_issues(issues, verbose)
        elif not dry_run:
            self.stdout.write(self.style.WARNING(
                '\nTo automatically fix issues, run with --fix flag'
            ))

    def analyze_database(self, verbose=False):
        """Analyze database for issues."""
        issues = {
            'orphaned': {},
            'invalid': {},
            'inconsistent': {},
            'duplicates': {},
            'empty': {},
        }

        # Import models
        from catalog.models import (
            Product, Variant, ProductAttributeValue, ProductType,
            Attribute, AttributeValue, ProductTypeAttribute,
            ProductVariantAxis, ChannelVariantAxis, ChannelListingAxis,
            BundleComponent,
        )
        from pub.models import ChannelListing, ChannelListingMap
        from importer.models import ProductImport, ImportRow, CategoryBatch, AttributeMapping

        self.stdout.write('Analyzing database structure...\n')

        # 1. Orphaned ProductAttributeValue records
        self.stdout.write('  Checking ProductAttributeValue...')
        orphaned_pav = ProductAttributeValue.objects.filter(
            Q(product__isnull=True, variant__isnull=True) |
            Q(product__isnull=False, variant__isnull=False)
        )
        if orphaned_pav.exists():
            issues['orphaned']['ProductAttributeValue'] = orphaned_pav.count()
            if verbose:
                self.stdout.write(f'    ⚠️  Found {orphaned_pav.count()} invalid records')

        # ProductAttributeValue with invalid product references
        invalid_product_pav = ProductAttributeValue.objects.filter(
            product__isnull=False
        ).exclude(product__in=Product.objects.all())
        if invalid_product_pav.exists():
            issues['invalid']['ProductAttributeValue.invalid_product'] = invalid_product_pav.count()

        # ProductAttributeValue with invalid variant references
        invalid_variant_pav = ProductAttributeValue.objects.filter(
            variant__isnull=False
        ).exclude(variant__in=Variant.objects.all())
        if invalid_variant_pav.exists():
            issues['invalid']['ProductAttributeValue.invalid_variant'] = invalid_variant_pav.count()

        # 2. Orphaned Variants (variants without products)
        self.stdout.write('  Checking Variants...')
        orphaned_variants = Variant.objects.filter(product__isnull=True)
        if orphaned_variants.exists():
            issues['orphaned']['Variant'] = orphaned_variants.count()
            if verbose:
                self.stdout.write(f'    ⚠️  Found {orphaned_variants.count()} orphaned variants')

        # Variants with invalid product references
        invalid_product_variants = Variant.objects.exclude(
            product__in=Product.objects.all()
        )
        if invalid_product_variants.exists():
            issues['invalid']['Variant.invalid_product'] = invalid_product_variants.count()

        # 3. Products with invalid product_type references
        self.stdout.write('  Checking Products...')
        invalid_pt_products = Product.objects.exclude(
            product_type__in=ProductType.objects.all()
        )
        if invalid_pt_products.exists():
            issues['invalid']['Product.invalid_product_type'] = invalid_pt_products.count()

        # 4. Orphaned axes
        self.stdout.write('  Checking Variant Axes...')
        orphaned_pva = ProductVariantAxis.objects.exclude(
            product__in=Product.objects.all()
        )
        if orphaned_pva.exists():
            issues['orphaned']['ProductVariantAxis'] = orphaned_pva.count()

        orphaned_cva = ChannelVariantAxis.objects.exclude(
            product__in=Product.objects.all()
        )
        if orphaned_cva.exists():
            issues['orphaned']['ChannelVariantAxis'] = orphaned_cva.exists()

        # 5. Orphaned BundleComponents
        self.stdout.write('  Checking BundleComponents...')
        orphaned_bundles = BundleComponent.objects.filter(
            Q(bundle_variant__isnull=True) |
            Q(component_variant__isnull=True)
        )
        if orphaned_bundles.exists():
            issues['orphaned']['BundleComponent'] = orphaned_bundles.count()

        # BundleComponents with invalid variant references
        invalid_bundle = BundleComponent.objects.exclude(
            bundle_variant__in=Variant.objects.all()
        )
        if invalid_bundle.exists():
            issues['invalid']['BundleComponent.invalid_bundle_variant'] = invalid_bundle.count()

        invalid_component = BundleComponent.objects.exclude(
            component_variant__in=Variant.objects.all()
        )
        if invalid_component.exists():
            issues['invalid']['BundleComponent.invalid_component_variant'] = invalid_component.count()

        # 6. Orphaned ChannelListingAxis
        self.stdout.write('  Checking ChannelListingAxis...')
        try:
            orphaned_cla = ChannelListingAxis.objects.exclude(
                listing__in=ChannelListing.objects.all()
            )
            if orphaned_cla.exists():
                issues['orphaned']['ChannelListingAxis'] = orphaned_cla.count()
        except Exception:
            pass

        # 7. Orphaned ChannelListingMap
        self.stdout.write('  Checking ChannelListingMap...')
        try:
            orphaned_clm = ChannelListingMap.objects.filter(
                Q(variant__isnull=True) | Q(listing__isnull=True)
            )
            if orphaned_clm.exists():
                issues['orphaned']['ChannelListingMap'] = orphaned_clm.count()

            invalid_variant_clm = ChannelListingMap.objects.exclude(
                variant__in=Variant.objects.all()
            )
            if invalid_variant_clm.exists():
                issues['invalid']['ChannelListingMap.invalid_variant'] = invalid_variant_clm.count()
        except Exception:
            pass

        # 8. Products without variants
        self.stdout.write('  Checking Products without variants...')
        products_no_variants = Product.objects.annotate(
            variant_count=Count('variants')
        ).filter(variant_count=0)
        if products_no_variants.exists():
            issues['empty']['Product.no_variants'] = products_no_variants.count()
            if verbose:
                self.stdout.write(f'    ⚠️  Found {products_no_variants.count()} products without variants')

        # 9. ProductTypes without products
        self.stdout.write('  Checking ProductTypes...')
        product_types_no_products = ProductType.objects.annotate(
            product_count=Count('products')
        ).filter(product_count=0)
        if product_types_no_products.exists():
            issues['empty']['ProductType.no_products'] = product_types_no_products.count()

        # 10. Attributes without values
        self.stdout.write('  Checking Attributes...')
        attributes_no_values = Attribute.objects.annotate(
            value_count=Count('values')
        ).filter(value_count=0)
        if attributes_no_values.exists():
            issues['empty']['Attribute.no_values'] = attributes_no_values.count()

        # 11. ProductTypeAttributes with invalid references
        self.stdout.write('  Checking ProductTypeAttributes...')
        invalid_pta = ProductTypeAttribute.objects.filter(
            Q(product_type__isnull=True) | Q(attribute__isnull=True)
        )
        if invalid_pta.exists():
            issues['invalid']['ProductTypeAttribute'] = invalid_pta.count()

        # 12. Import-related orphaned records
        self.stdout.write('  Checking Import records...')
        try:
            from importer.models import ProductImport
            orphaned_rows = ImportRow.objects.exclude(
                product_import__in=ProductImport.objects.all()
            )
            if orphaned_rows.exists():
                issues['orphaned']['ImportRow'] = orphaned_rows.count()

            orphaned_batches = CategoryBatch.objects.exclude(
                product_import__in=ProductImport.objects.all()
            )
            if orphaned_batches.exists():
                issues['orphaned']['CategoryBatch'] = orphaned_batches.count()

            orphaned_mappings = AttributeMapping.objects.exclude(
                category_batch__in=CategoryBatch.objects.all()
            )
            if orphaned_mappings.exists():
                issues['orphaned']['AttributeMapping'] = orphaned_mappings.count()
        except Exception:
            pass

        # 13. Duplicate SKUs (should be unique)
        self.stdout.write('  Checking for duplicate SKUs...')
        from django.db.models import Count
        duplicate_skus = Variant.objects.values('sku').annotate(
            count=Count('sku')
        ).filter(count__gt=1, sku__isnull=False).exclude(sku='')
        if duplicate_skus.exists():
            issues['duplicates']['Variant.duplicate_sku'] = duplicate_skus.count()

        # 14. Duplicate product codes (should be unique)
        duplicate_codes = Product.objects.values('code').annotate(
            count=Count('code')
        ).filter(count__gt=1).exclude(code='')
        if duplicate_codes.exists():
            issues['duplicates']['Product.duplicate_code'] = duplicate_codes.count()

        self.stdout.write('  ✓ Analysis complete\n')
        return issues

    def report_issues(self, issues, verbose=False):
        """Report found issues."""
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('DATABASE CLEANUP REPORT'))
        self.stdout.write('=' * 80 + '\n')

        total_issues = sum(
            sum(category.values()) if isinstance(category, dict) else 0
            for category in issues.values()
        )

        if total_issues == 0:
            self.stdout.write(self.style.SUCCESS('✅ Database is clean! No issues found.\n'))
            return

        # Orphaned records
        if issues['orphaned']:
            self.stdout.write(self.style.WARNING('🔴 ORPHANED RECORDS (broken foreign keys):'))
            for model, count in sorted(issues['orphaned'].items()):
                self.stdout.write(f'  • {model}: {count} records')
            self.stdout.write('')

        # Invalid references
        if issues['invalid']:
            self.stdout.write(self.style.ERROR('🔴 INVALID REFERENCES:'))
            for ref, count in sorted(issues['invalid'].items()):
                self.stdout.write(f'  • {ref}: {count} records')
            self.stdout.write('')

        # Duplicates
        if issues['duplicates']:
            self.stdout.write(self.style.WARNING('🟡 DUPLICATE RECORDS:'))
            for dup, count in sorted(issues['duplicates'].items()):
                self.stdout.write(f'  • {dup}: {count} groups')
            self.stdout.write('')

        # Empty/Unused
        if issues['empty']:
            self.stdout.write(self.style.WARNING('🟡 EMPTY/UNUSED RECORDS:'))
            for empty, count in sorted(issues['empty'].items()):
                self.stdout.write(f'  • {empty}: {count} records')
            self.stdout.write('')

        self.stdout.write(f'\n📊 Total issues found: {total_issues}\n')

    def fix_issues(self, issues, verbose=False):
        """Fix issues automatically where possible."""
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('FIXING ISSUES'))
        self.stdout.write('=' * 80 + '\n')

        from catalog.models import (
            Product, Variant, ProductAttributeValue,
            ProductVariantAxis, ChannelVariantAxis, ChannelListingAxis,
            BundleComponent,
        )
        from pub.models import ChannelListingMap
        from importer.models import ImportRow, CategoryBatch, AttributeMapping, ProductImport

        fixed_count = 0

        with transaction.atomic():
            # Fix orphaned ProductAttributeValue
            if 'ProductAttributeValue' in issues.get('orphaned', {}):
                orphaned = ProductAttributeValue.objects.filter(
                    Q(product__isnull=True, variant__isnull=True) |
                    Q(product__isnull=False, variant__isnull=False)
                )
                count = orphaned.count()
                orphaned.delete()
                self.stdout.write(f'  ✓ Deleted {count} invalid ProductAttributeValue records')
                fixed_count += count

            # Fix invalid ProductAttributeValue references
            if 'ProductAttributeValue.invalid_product' in issues.get('invalid', {}):
                invalid = ProductAttributeValue.objects.filter(
                    product__isnull=False
                ).exclude(product__in=Product.objects.all())
                count = invalid.count()
                invalid.delete()
                self.stdout.write(f'  ✓ Deleted {count} ProductAttributeValue with invalid product references')
                fixed_count += count

            if 'ProductAttributeValue.invalid_variant' in issues.get('invalid', {}):
                invalid = ProductAttributeValue.objects.filter(
                    variant__isnull=False
                ).exclude(variant__in=Variant.objects.all())
                count = invalid.count()
                invalid.delete()
                self.stdout.write(f'  ✓ Deleted {count} ProductAttributeValue with invalid variant references')
                fixed_count += count

            # Fix orphaned variants (shouldn't happen due to CASCADE, but check anyway)
            if 'Variant' in issues.get('orphaned', {}):
                orphaned = Variant.objects.filter(product__isnull=True)
                count = orphaned.count()
                orphaned.delete()
                self.stdout.write(f'  ✓ Deleted {count} orphaned Variant records')
                fixed_count += count

            # Fix orphaned axes
            if 'ProductVariantAxis' in issues.get('orphaned', {}):
                orphaned = ProductVariantAxis.objects.exclude(
                    product__in=Product.objects.all()
                )
                count = orphaned.count()
                orphaned.delete()
                self.stdout.write(f'  ✓ Deleted {count} orphaned ProductVariantAxis records')
                fixed_count += count

            if 'ChannelVariantAxis' in issues.get('orphaned', {}):
                orphaned = ChannelVariantAxis.objects.exclude(
                    product__in=Product.objects.all()
                )
                count = orphaned.count()
                orphaned.delete()
                self.stdout.write(f'  ✓ Deleted {count} orphaned ChannelVariantAxis records')
                fixed_count += count

            # Fix orphaned BundleComponents
            if 'BundleComponent' in issues.get('orphaned', {}):
                orphaned = BundleComponent.objects.filter(
                    Q(bundle_variant__isnull=True) |
                    Q(component_variant__isnull=True)
                )
                count = orphaned.count()
                orphaned.delete()
                self.stdout.write(f'  ✓ Deleted {count} orphaned BundleComponent records')
                fixed_count += count

            # Fix invalid BundleComponent references
            if 'BundleComponent.invalid_bundle_variant' in issues.get('invalid', {}):
                invalid = BundleComponent.objects.exclude(
                    bundle_variant__in=Variant.objects.all()
                )
                count = invalid.count()
                invalid.delete()
                self.stdout.write(f'  ✓ Deleted {count} BundleComponent with invalid bundle_variant')
                fixed_count += count

            if 'BundleComponent.invalid_component_variant' in issues.get('invalid', {}):
                invalid = BundleComponent.objects.exclude(
                    component_variant__in=Variant.objects.all()
                )
                count = invalid.count()
                invalid.delete()
                self.stdout.write(f'  ✓ Deleted {count} BundleComponent with invalid component_variant')
                fixed_count += count

            # Fix orphaned ChannelListingAxis
            if 'ChannelListingAxis' in issues.get('orphaned', {}):
                try:
                    orphaned = ChannelListingAxis.objects.exclude(
                        listing__in=ChannelListing.objects.all()
                    )
                    count = orphaned.count()
                    orphaned.delete()
                    self.stdout.write(f'  ✓ Deleted {count} orphaned ChannelListingAxis records')
                    fixed_count += count
                except Exception as e:
                    if verbose:
                        self.stdout.write(self.style.ERROR(f'  ✗ Error fixing ChannelListingAxis: {e}'))

            # Fix orphaned ChannelListingMap
            if 'ChannelListingMap' in issues.get('orphaned', {}):
                try:
                    orphaned = ChannelListingMap.objects.filter(
                        Q(variant__isnull=True) | Q(listing__isnull=True)
                    )
                    count = orphaned.count()
                    orphaned.delete()
                    self.stdout.write(f'  ✓ Deleted {count} orphaned ChannelListingMap records')
                    fixed_count += count
                except Exception as e:
                    if verbose:
                        self.stdout.write(self.style.ERROR(f'  ✗ Error fixing ChannelListingMap: {e}'))

            # Fix orphaned import records
            if 'ImportRow' in issues.get('orphaned', {}):
                orphaned = ImportRow.objects.exclude(
                    product_import__in=ProductImport.objects.all()
                )
                count = orphaned.count()
                orphaned.delete()
                self.stdout.write(f'  ✓ Deleted {count} orphaned ImportRow records')
                fixed_count += count

            if 'CategoryBatch' in issues.get('orphaned', {}):
                orphaned = CategoryBatch.objects.exclude(
                    product_import__in=ProductImport.objects.all()
                )
                count = orphaned.count()
                orphaned.delete()
                self.stdout.write(f'  ✓ Deleted {count} orphaned CategoryBatch records')
                fixed_count += count

            if 'AttributeMapping' in issues.get('orphaned', {}):
                orphaned = AttributeMapping.objects.exclude(
                    category_batch__in=CategoryBatch.objects.all()
                )
                count = orphaned.count()
                orphaned.delete()
                self.stdout.write(f'  ✓ Deleted {count} orphaned AttributeMapping records')
                fixed_count += count

        self.stdout.write(f'\n✅ Fixed {fixed_count} issues\n')

        # Note about issues that can't be auto-fixed
        if issues.get('duplicates') or issues.get('empty'):
            self.stdout.write(self.style.WARNING(
                '\n⚠️  Some issues require manual review:\n'
                '  • Duplicate records (need manual deduplication)\n'
                '  • Empty/unused records (may be intentional)\n'
            ))
