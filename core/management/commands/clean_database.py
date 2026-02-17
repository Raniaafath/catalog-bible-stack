"""
Complete database cleanup command.

Deletes ALL data from all apps while preserving system configuration:
- Keeps: Locale, Channel, ExportProfile, Django auth tables
- Deletes: Everything else (catalog, content, importer, kw, pub data)

Usage:
    python manage.py clean_database           # Interactive (asks for confirmation)
    python manage.py clean_database --no-input  # Non-interactive
"""
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Clean the entire database - removes all data except system configuration (Locale, Channel)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-input',
            action='store_true',
            help='Skip confirmation prompt',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n=== DRY RUN MODE - No changes will be made ===\n'))
        
        # Print summary first
        self.print_summary()
        
        if not options['no_input'] and not dry_run:
            confirm = input(
                '\n⚠️  WARNING: This will delete ALL data from the database!\n'
                '    (Locale and Channel records will be preserved)\n'
                'Are you sure you want to continue? (yes/no): '
            )
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.WARNING('Operation cancelled.'))
                return

        if dry_run:
            self.stdout.write(self.style.WARNING('\nDry run complete. No data was deleted.'))
            return

        self.stdout.write(self.style.WARNING('\nCleaning database...\n'))
        
        with transaction.atomic():
            self.clean_all()

        self.stdout.write(self.style.SUCCESS('\n✅ Database cleaned successfully!'))
        self.stdout.write('   Preserved: Locale, Channel, ExportProfile, Django auth tables')

    def print_summary(self):
        """Print current data summary."""
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write('CURRENT DATA SUMMARY')
        self.stdout.write('=' * 70)
        
        counts = {}
        
        # Content models
        try:
            from content.models import (
                ProductI18n, ProductAttributeValueI18n, AttributeI18n,
                ProductTypeI18n, AttributeValueI18n, ProductTypeSynonym,
                AttributeValueSynonym, ContentBlock, TranslationTask,
                ProductMedia, ComplianceClaim,
            )
            counts['content.ProductI18n'] = ProductI18n.objects.count()
            counts['content.ProductAttributeValueI18n'] = ProductAttributeValueI18n.objects.count()
            counts['content.AttributeI18n'] = AttributeI18n.objects.count()
            counts['content.ProductTypeI18n'] = ProductTypeI18n.objects.count()
            counts['content.AttributeValueI18n'] = AttributeValueI18n.objects.count()
            counts['content.ProductTypeSynonym'] = ProductTypeSynonym.objects.count()
            counts['content.AttributeValueSynonym'] = AttributeValueSynonym.objects.count()
            counts['content.ContentBlock'] = ContentBlock.objects.count()
            counts['content.TranslationTask'] = TranslationTask.objects.count()
            counts['content.ProductMedia'] = ProductMedia.objects.count()
            counts['content.ComplianceClaim'] = ComplianceClaim.objects.count()
        except ImportError:
            pass
        
        # Keyword models
        try:
            from kw.models import (
                Keyword, PlannerSeed, PlannerRun, PlannerRunSeed, PlannerRunKeyword,
                Metric, Concept, KeywordConcept, ProductTypeMap, KeywordParse,
                AttributeMap, ProductKeywordMap, MappingRun, Candidate, Source,
            )
            counts['kw.Keyword'] = Keyword.objects.count()
            counts['kw.PlannerSeed'] = PlannerSeed.objects.count()
            counts['kw.PlannerRun'] = PlannerRun.objects.count()
            counts['kw.PlannerRunSeed'] = PlannerRunSeed.objects.count()
            counts['kw.PlannerRunKeyword'] = PlannerRunKeyword.objects.count()
            counts['kw.Metric'] = Metric.objects.count()
            counts['kw.Concept'] = Concept.objects.count()
            counts['kw.KeywordConcept'] = KeywordConcept.objects.count()
            counts['kw.ProductTypeMap'] = ProductTypeMap.objects.count()
            counts['kw.KeywordParse'] = KeywordParse.objects.count()
            counts['kw.AttributeMap'] = AttributeMap.objects.count()
            counts['kw.ProductKeywordMap'] = ProductKeywordMap.objects.count()
            counts['kw.MappingRun'] = MappingRun.objects.count()
            counts['kw.Candidate'] = Candidate.objects.count()
            counts['kw.Source'] = Source.objects.count()
        except ImportError:
            pass
        
        # Pub models
        try:
            from pub.models import (
                ChannelPolicySet, ChannelLocalePolicy, ChannelConstraintPolicy,
                ChannelBundlePolicy, ChannelProductOption, ChannelProductOptionI18n,
                ChannelProductOptionAttribute, Template, TemplatePart,
                GenerationRun, TitleSelection, GenerationOutput, Approval,
                ChannelListing, ChannelListingMap, ContentSelection,
                ContentEditSession, ContentSet, ContentSetItem,
                GenerationBatch, GenerationBatchItem, ExportJob,
                UniqueTitle, TermGlossary,
            )
            counts['pub.ChannelPolicySet'] = ChannelPolicySet.objects.count()
            counts['pub.ChannelLocalePolicy'] = ChannelLocalePolicy.objects.count()
            counts['pub.ChannelConstraintPolicy'] = ChannelConstraintPolicy.objects.count()
            counts['pub.ChannelBundlePolicy'] = ChannelBundlePolicy.objects.count()
            counts['pub.ChannelProductOption'] = ChannelProductOption.objects.count()
            counts['pub.ChannelProductOptionI18n'] = ChannelProductOptionI18n.objects.count()
            counts['pub.ChannelProductOptionAttribute'] = ChannelProductOptionAttribute.objects.count()
            counts['pub.Template'] = Template.objects.count()
            counts['pub.TemplatePart'] = TemplatePart.objects.count()
            counts['pub.GenerationRun'] = GenerationRun.objects.count()
            counts['pub.TitleSelection'] = TitleSelection.objects.count()
            counts['pub.GenerationOutput'] = GenerationOutput.objects.count()
            counts['pub.Approval'] = Approval.objects.count()
            counts['pub.ChannelListing'] = ChannelListing.objects.count()
            counts['pub.ChannelListingMap'] = ChannelListingMap.objects.count()
            counts['pub.ContentSelection'] = ContentSelection.objects.count()
            counts['pub.ContentEditSession'] = ContentEditSession.objects.count()
            counts['pub.ContentSet'] = ContentSet.objects.count()
            counts['pub.ContentSetItem'] = ContentSetItem.objects.count()
            counts['pub.GenerationBatch'] = GenerationBatch.objects.count()
            counts['pub.GenerationBatchItem'] = GenerationBatchItem.objects.count()
            counts['pub.ExportJob'] = ExportJob.objects.count()
            counts['pub.UniqueTitle'] = UniqueTitle.objects.count()
            counts['pub.TermGlossary'] = TermGlossary.objects.count()
        except ImportError:
            pass
        
        # Importer models
        try:
            from importer.models import (
                ProductImport, ImportColumnMap, ImportRow,
                CategoryBatch, AttributeMapping, ImportColumnRule,
            )
            counts['importer.ProductImport'] = ProductImport.objects.count()
            counts['importer.ImportColumnMap'] = ImportColumnMap.objects.count()
            counts['importer.ImportRow'] = ImportRow.objects.count()
            counts['importer.CategoryBatch'] = CategoryBatch.objects.count()
            counts['importer.AttributeMapping'] = AttributeMapping.objects.count()
            counts['importer.ImportColumnRule'] = ImportColumnRule.objects.count()
        except ImportError:
            pass
        
        # Catalog models
        try:
            from catalog.models import (
                Product, Variant, ProductAttributeValue,
                ProductType, Attribute, AttributeValue, ProductTypeAttribute,
                ProductVariantAxis, ChannelVariantAxis, BundleComponent,
                ChannelListingAxis,
            )
            counts['catalog.Product'] = Product.objects.count()
            counts['catalog.Variant'] = Variant.objects.count()
            counts['catalog.ProductAttributeValue'] = ProductAttributeValue.objects.count()
            counts['catalog.ProductType'] = ProductType.objects.count()
            counts['catalog.Attribute'] = Attribute.objects.count()
            counts['catalog.AttributeValue'] = AttributeValue.objects.count()
            counts['catalog.ProductTypeAttribute'] = ProductTypeAttribute.objects.count()
            counts['catalog.ProductVariantAxis'] = ProductVariantAxis.objects.count()
            counts['catalog.ChannelVariantAxis'] = ChannelVariantAxis.objects.count()
            counts['catalog.BundleComponent'] = BundleComponent.objects.count()
            counts['catalog.ChannelListingAxis'] = ChannelListingAxis.objects.count()
        except ImportError:
            pass
        
        # Group by app
        apps = {}
        for key, count in counts.items():
            app = key.split('.')[0]
            if app not in apps:
                apps[app] = {}
            apps[app][key] = count
        
        total = 0
        for app_name, app_counts in sorted(apps.items()):
            app_total = sum(app_counts.values())
            if app_total > 0:
                self.stdout.write(f'\n{app_name}:')
                for key, count in sorted(app_counts.items()):
                    if count > 0:
                        model_name = key.split('.')[1]
                        self.stdout.write(f'  {model_name}: {count}')
                total += app_total
        
        self.stdout.write(f'\n{"=" * 70}')
        self.stdout.write(f'Total records to delete: {total}')
        self.stdout.write('=' * 70)

    def clean_all(self):
        """Delete all data in correct dependency order."""
        
        # ===== 1. CONTENT / TRANSLATION DATA =====
        self.stdout.write('\n[1/6] Cleaning content/translation data...')
        try:
            from content.models import (
                ProductI18n, ProductAttributeValueI18n, AttributeI18n,
                ProductTypeI18n, AttributeValueI18n, ProductTypeSynonym,
                AttributeValueSynonym, ContentBlock, TranslationTask,
                ProductMedia, ComplianceClaim,
            )
            self._delete_model(ProductI18n)
            self._delete_model(ProductAttributeValueI18n)
            self._delete_model(AttributeI18n)
            self._delete_model(ProductTypeI18n)
            self._delete_model(AttributeValueI18n)
            self._delete_model(ProductTypeSynonym)
            self._delete_model(AttributeValueSynonym)
            self._delete_model(ContentBlock)
            self._delete_model(TranslationTask)
            self._delete_model(ProductMedia)
            self._delete_model(ComplianceClaim)
        except ImportError as e:
            self.stdout.write(f'  Skipping content app (not installed): {e}')
        
        # ===== 2. KEYWORD DATA =====
        self.stdout.write('\n[2/6] Cleaning keyword data...')
        try:
            from kw.models import (
                Candidate, MappingRun, ProductKeywordMap, AttributeMap,
                KeywordParse, ProductTypeMap, KeywordConcept, Concept,
                Metric, PlannerRunKeyword, PlannerRunSeed, Keyword,
                PlannerRun, PlannerSeed, Source,
            )
            self._delete_model(Candidate)
            self._delete_model(MappingRun)
            self._delete_model(ProductKeywordMap)
            self._delete_model(AttributeMap)
            self._delete_model(KeywordParse)
            self._delete_model(ProductTypeMap)
            self._delete_model(KeywordConcept)
            self._delete_model(Concept)
            self._delete_model(Metric)
            self._delete_model(PlannerRunKeyword)
            self._delete_model(PlannerRunSeed)
            self._delete_model(Keyword)
            self._delete_model(PlannerRun)
            self._delete_model(PlannerSeed)
            self._delete_model(Source)
        except ImportError as e:
            self.stdout.write(f'  Skipping kw app (not installed): {e}')
        
        # ===== 3. PUB / GENERATION DATA =====
        self.stdout.write('\n[3/6] Cleaning pub/generation data...')
        try:
            from pub.models import (
                GenerationBatchItem, GenerationOutput, GenerationBatch,
                GenerationRun, TitleSelection, ContentSelection,
                ContentEditSession, ContentSetItem, ContentSet,
                ExportJob, UniqueTitle, TermGlossary, Approval,
                TemplatePart, Template,
                ChannelLocalePolicy, ChannelConstraintPolicy, ChannelBundlePolicy,
                ChannelPolicySet,
                ChannelProductOptionAttribute, ChannelProductOptionI18n, ChannelProductOption,
            )
            self._delete_model(GenerationBatchItem)
            self._delete_model(GenerationOutput)
            self._delete_model(GenerationBatch)
            self._delete_model(GenerationRun)
            self._delete_model(TitleSelection)
            self._delete_model(ContentSelection)
            self._delete_model(ContentEditSession)
            self._delete_model(ContentSetItem)
            self._delete_model(ContentSet)
            self._delete_model(ExportJob)
            self._delete_model(UniqueTitle)
            self._delete_model(TermGlossary)
            self._delete_model(Approval)
            self._delete_model(TemplatePart)
            self._delete_model(Template)
            self._delete_model(ChannelLocalePolicy)
            self._delete_model(ChannelConstraintPolicy)
            self._delete_model(ChannelBundlePolicy)
            self._delete_model(ChannelPolicySet)
            self._delete_model(ChannelProductOptionAttribute)
            self._delete_model(ChannelProductOptionI18n)
            self._delete_model(ChannelProductOption)
        except ImportError as e:
            self.stdout.write(f'  Skipping pub app (not installed): {e}')
        
        # ===== 4. LISTING / AXIS DATA =====
        self.stdout.write('\n[4/6] Cleaning listing/axis data...')
        try:
            from catalog.models import (
                ChannelListingAxis, ChannelVariantAxis, ProductVariantAxis,
            )
            from pub.models import ChannelListingMap, ChannelListing
            
            self._delete_model(ChannelListingAxis)
            self._delete_model(ChannelListingMap)
            self._delete_model(ChannelListing)
            self._delete_model(ChannelVariantAxis)
            self._delete_model(ProductVariantAxis)
        except ImportError as e:
            self.stdout.write(f'  Skipping listing data: {e}')
        
        # ===== 5. IMPORT DATA =====
        self.stdout.write('\n[5/6] Cleaning import data...')
        try:
            from importer.models import (
                AttributeMapping, CategoryBatch, ImportRow,
                ImportColumnMap, ImportColumnRule, ProductImport,
            )
            self._delete_model(AttributeMapping)
            self._delete_model(CategoryBatch)
            self._delete_model(ImportRow)
            self._delete_model(ImportColumnMap)
            self._delete_model(ImportColumnRule)
            self._delete_model(ProductImport)
        except ImportError as e:
            self.stdout.write(f'  Skipping importer app (not installed): {e}')
        
        # ===== 6. CORE CATALOG DATA =====
        self.stdout.write('\n[6/6] Cleaning catalog data...')
        try:
            from catalog.models import (
                ProductAttributeValue, BundleComponent, Variant, Product,
                ProductTypeAttribute, AttributeValue, Attribute, ProductType,
            )
            self._delete_model(ProductAttributeValue)
            self._delete_model(BundleComponent)
            self._delete_model(Variant)
            self._delete_model(Product)
            self._delete_model(ProductTypeAttribute)
            self._delete_model(AttributeValue)
            self._delete_model(Attribute)
            self._delete_model(ProductType)
        except ImportError as e:
            self.stdout.write(f'  Skipping catalog app (not installed): {e}')

    def _delete_model(self, model):
        """Delete all records from a model and print result."""
        try:
            count = model.objects.count()
            if count > 0:
                deleted, _ = model.objects.all().delete()
                self.stdout.write(f'  ✓ Deleted {deleted} {model.__name__} records')
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  ⚠ Error deleting {model.__name__}: {e}'))
