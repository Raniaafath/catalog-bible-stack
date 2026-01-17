from django.core.management.base import BaseCommand

from catalog.models import Attribute, AttributeValue, ProductAttributeValue, ProductType
from content.models import (
    AttributeI18n,
    AttributeValueI18n,
    Locale,
    ProductAttributeValueI18n,
    ProductTypeI18n,
    TranslationTask,
)


class Command(BaseCommand):
    help = "Enqueue translation tasks for missing i18n labels for a given target locale."

    def add_arguments(self, parser):
        parser.add_argument("--locale", required=True, help="Target locale code, e.g. en or de")
        parser.add_argument(
            "--scopes",
            default="attribute,attribute_value,product_type,product_attribute_value",
            help="Comma-separated list of scopes to process.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=25,
            help="Number of items per translation task.",
        )

    def handle(self, *args, **options):
        locale_code = options["locale"]
        scopes = [s.strip() for s in options["scopes"].split(",") if s.strip()]
        batch_size = options["batch_size"]

        locale, _ = Locale.objects.get_or_create(code=locale_code, defaults={"name": locale_code})

        total_tasks = 0
        for scope in scopes:
            missing_ids = self._missing_ids(scope, locale)
            if not missing_ids:
                self.stdout.write(self.style.WARNING(f"No missing translations for scope={scope} locale={locale_code}"))
                continue
            for i in range(0, len(missing_ids), batch_size):
                ids_chunk = missing_ids[i : i + batch_size]
                task = TranslationTask.objects.create(
                    locale=locale.code,
                    scope=scope,
                    target_ids=ids_chunk,
                    status=TranslationTask.Status.PENDING,
                )
                total_tasks += 1
                self.stdout.write(self.style.SUCCESS(f"Enqueued {scope} task {task.id} ({len(ids_chunk)} items)"))
        self.stdout.write(self.style.SUCCESS(f"Done. Created {total_tasks} tasks."))

    def _missing_ids(self, scope: str, locale: Locale):
        if scope == "attribute":
            existing = set(AttributeI18n.objects.filter(locale=locale).values_list("attribute_id", flat=True))
            all_ids = set(Attribute.objects.values_list("id", flat=True))
            return sorted(all_ids - existing)
        if scope == "attribute_value":
            existing = set(AttributeValueI18n.objects.filter(locale=locale).values_list("attribute_value_id", flat=True))
            all_ids = set(AttributeValue.objects.values_list("id", flat=True))
            return sorted(all_ids - existing)
        if scope == "product_type":
            existing = set(ProductTypeI18n.objects.filter(locale=locale).values_list("product_type_id", flat=True))
            all_ids = set(ProductType.objects.values_list("id", flat=True))
            return sorted(all_ids - existing)
        if scope == "product_attribute_value":
            existing = set(
                ProductAttributeValueI18n.objects.filter(locale=locale).values_list(
                    "product_attribute_value_id", flat=True
                )
            )
            all_ids = set(
                ProductAttributeValue.objects.filter(value_text__isnull=False)
                .exclude(value_text="")
                .filter(attribute_value__isnull=True, attribute__is_value_translatable=True)
                .exclude(attribute__data_type=Attribute.DataType.ENUM)
                .values_list("id", flat=True)
            )
            return sorted(all_ids - existing)
        raise ValueError(f"Unknown scope: {scope}")
