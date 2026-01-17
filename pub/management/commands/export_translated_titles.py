import csv
import sys
from typing import Dict, Iterable, List, Optional, Sequence

from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command

from catalog.models import Attribute, Product, ProductAttributeValue, ProductTypeAttribute, Variant
from content.models import AttributeI18n, AttributeValueI18n, Locale
from pub.models import Channel
from pub.services.title_renderer import TitleRenderError, render_title


class Command(BaseCommand):
    help = (
        "Generate template-based titles for selected products and export translated "
        "attributes to CSV (stdout by default)."
    )

    def add_arguments(self, parser):
        parser.add_argument("--locale", help="Target locale code, e.g. de or fr-CA.")
        parser.add_argument("--channel", help="Channel code for title templates, e.g. shopify.")
        parser.add_argument("--product-type-id", type=int, help="Filter by ProductType id.")
        parser.add_argument("--product-type-code", help="Filter by ProductType code.")
        parser.add_argument("--product-ids", help="Comma-separated Product ids.")
        parser.add_argument("--product-codes", help="Comma-separated Product codes.")
        parser.add_argument("--limit-products", type=int, default=None, help="Limit number of products.")
        parser.add_argument("--limit-variants", type=int, default=None, help="Limit number of variants per product.")
        parser.add_argument(
            "--output",
            help="Optional CSV path. If omitted, writes to stdout.",
        )
        parser.add_argument(
            "--skip-translation",
            action="store_true",
            help="Skip enqueue/run translation tasks for missing labels.",
        )
        parser.add_argument(
            "--translation-task-limit",
            type=int,
            default=25,
            help="Max translation tasks to process when running translation.",
        )
        parser.add_argument(
            "--translation-batch-size",
            type=int,
            default=200,
            help="Batch size for enqueueing missing translations.",
        )

    def handle(self, *args, **options):
        locale_code = options.get("locale") or self._prompt("Locale code")
        channel_code = options.get("channel") or self._prompt("Channel code")
        product_type_id = options.get("product_type_id")
        product_type_code = options.get("product_type_code")
        product_ids = self._parse_id_list(options.get("product_ids"))
        product_codes = self._parse_code_list(options.get("product_codes"))
        limit_products = options.get("limit_products")
        limit_variants = options.get("limit_variants")
        output_path = options.get("output")

        if not any([product_type_id, product_type_code, product_ids, product_codes]):
            selection = self._prompt("Select scope: 1) product type 2) products")
            if selection == "1":
                pt_value = self._prompt("Product type code or id")
                if pt_value.isdigit():
                    product_type_id = int(pt_value)
                else:
                    product_type_code = pt_value
            elif selection == "2":
                id_or_code = self._prompt("Select product keys: 1) ids 2) codes")
                if id_or_code == "1":
                    product_ids = self._parse_id_list(self._prompt("Product ids (comma-separated)"))
                elif id_or_code == "2":
                    product_codes = self._parse_code_list(self._prompt("Product codes (comma-separated)"))
                else:
                    raise CommandError("Invalid product selection option.")
            else:
                raise CommandError("Invalid scope selection.")

        if not options.get("skip_translation"):
            self._ensure_translations(
                locale_code=locale_code,
                batch_size=options["translation_batch_size"],
                limit=options["translation_task_limit"],
            )

        locale = self._get_locale(locale_code)
        channel = self._get_channel(channel_code)

        products = self._resolve_products(
            product_type_id=product_type_id,
            product_type_code=product_type_code,
            product_ids=product_ids,
            product_codes=product_codes,
            limit_products=limit_products,
        )
        if not products:
            raise CommandError("No products matched the selection.")

        product_types = sorted({p.product_type_id for p in products})
        attributes = self._load_attributes(product_types)
        attribute_labels = self._load_attribute_labels(attributes, locale)

        pavs = list(
            ProductAttributeValue.objects.filter(
                product_id__in=[p.id for p in products]
            ).select_related("attribute", "attribute_value")
        )
        variant_pavs = list(
            ProductAttributeValue.objects.filter(
                variant_id__in=Variant.objects.filter(product__in=products).values("id")
            ).select_related("attribute", "attribute_value")
        )

        product_pavs_map = self._index_pavs_by_product(pavs)
        variant_pavs_map = self._index_pavs_by_variant(variant_pavs)

        value_i18n_map = self._load_attribute_value_labels(
            pavs + variant_pavs,
            locale,
        )

        headers = self._build_headers(attributes, attribute_labels)
        writer, output_file = self._open_writer(output_path, headers)

        total_rows = 0
        for product in products:
            variants = list(product.variants.all().order_by("id"))
            if limit_variants:
                variants = variants[:limit_variants]
            if not variants:
                continue
            for variant in variants:
                total_rows += 1
                row = self._build_row(
                    product=product,
                    variant=variant,
                    locale=locale,
                    channel=channel,
                    attributes=attributes,
                    product_pavs=product_pavs_map.get(product.id, {}),
                    variant_pavs=variant_pavs_map.get(variant.id, {}),
                    value_i18n_map=value_i18n_map,
                )
                writer.writerow(row)

        if output_file is not sys.stdout:
            output_file.close()

        self.stdout.write(self.style.SUCCESS(f"Done. Exported {total_rows} rows."))

    def _prompt(self, message: str) -> str:
        return input(f"{message}: ").strip()

    def _parse_id_list(self, value: Optional[str]) -> List[int]:
        if not value:
            return []
        items = [v.strip() for v in value.split(",") if v.strip()]
        return [int(v) for v in items]

    def _parse_code_list(self, value: Optional[str]) -> List[str]:
        if not value:
            return []
        return [v.strip() for v in value.split(",") if v.strip()]

    def _ensure_translations(self, locale_code: str, batch_size: int, limit: int) -> None:
        self.stdout.write("Enqueueing missing translations (attribute, attribute_value)...")
        call_command(
            "enqueue_missing_translations",
            locale=locale_code,
            scopes="attribute,attribute_value",
            batch_size=batch_size,
        )
        self.stdout.write("Running translation tasks...")
        call_command("run_translation_tasks", locale=locale_code, limit=limit)

    def _get_locale(self, locale_code: str) -> Locale:
        locale, _ = Locale.objects.get_or_create(code=locale_code, defaults={"name": locale_code})
        return locale

    def _get_channel(self, channel_code: str) -> Channel:
        try:
            return Channel.objects.get(code=channel_code)
        except Channel.DoesNotExist as exc:
            raise CommandError(f"Channel {channel_code} not found") from exc

    def _resolve_products(
        self,
        *,
        product_type_id: Optional[int],
        product_type_code: Optional[str],
        product_ids: Sequence[int],
        product_codes: Sequence[str],
        limit_products: Optional[int],
    ) -> List[Product]:
        qs = Product.objects.select_related("product_type")

        if product_type_id or product_type_code:
            if product_type_id:
                qs = qs.filter(product_type_id=product_type_id)
            else:
                qs = qs.filter(product_type__code=product_type_code)
        elif product_ids:
            qs = qs.filter(id__in=product_ids)
        elif product_codes:
            qs = qs.filter(code__in=product_codes)
        else:
            raise CommandError("No product selection provided.")

        if limit_products:
            qs = qs.order_by("id")[:limit_products]
        return list(qs)

    def _load_attributes(self, product_type_ids: Sequence[int]) -> List[Attribute]:
        rows = (
            ProductTypeAttribute.objects.filter(product_type_id__in=product_type_ids)
            .select_related("attribute")
            .order_by("attribute__code")
        )
        seen = set()
        attributes = []
        for row in rows:
            if row.attribute_id not in seen:
                seen.add(row.attribute_id)
                attributes.append(row.attribute)
        return attributes

    def _load_attribute_labels(self, attributes: Sequence[Attribute], locale: Locale) -> Dict[int, str]:
        if not attributes:
            return {}
        labels = {
            row["attribute_id"]: row["label"]
            for row in AttributeI18n.objects.filter(
                attribute_id__in=[a.id for a in attributes],
                locale=locale,
            ).values("attribute_id", "label")
        }
        return labels

    def _load_attribute_value_labels(
        self,
        pavs: Sequence[ProductAttributeValue],
        locale: Locale,
    ) -> Dict[int, str]:
        value_ids = {pav.attribute_value_id for pav in pavs if pav.attribute_value_id}
        if not value_ids:
            return {}
        return {
            row["attribute_value_id"]: row["label"]
            for row in AttributeValueI18n.objects.filter(
                attribute_value_id__in=value_ids,
                locale=locale,
            ).values("attribute_value_id", "label")
        }

    def _index_pavs_by_product(
        self, pavs: Iterable[ProductAttributeValue]
    ) -> Dict[int, Dict[int, ProductAttributeValue]]:
        product_map: Dict[int, Dict[int, ProductAttributeValue]] = {}
        for pav in pavs:
            if not pav.product_id:
                continue
            product_map.setdefault(pav.product_id, {})[pav.attribute_id] = pav
        return product_map

    def _index_pavs_by_variant(
        self, pavs: Iterable[ProductAttributeValue]
    ) -> Dict[int, Dict[int, ProductAttributeValue]]:
        variant_map: Dict[int, Dict[int, ProductAttributeValue]] = {}
        for pav in pavs:
            if not pav.variant_id:
                continue
            variant_map.setdefault(pav.variant_id, {})[pav.attribute_id] = pav
        return variant_map

    def _build_headers(
        self, attributes: Sequence[Attribute], attribute_labels: Dict[int, str]
    ) -> List[str]:
        headers = [
            "product_id",
            "product_code",
            "variant_id",
            "variant_sku",
            "product_type",
            "locale",
            "channel",
            "title",
        ]
        for attr in attributes:
            label = attribute_labels.get(attr.id) or attr.code
            headers.append(f"{label} ({attr.code})")
        return headers

    def _open_writer(self, output_path: Optional[str], headers: Sequence[str]):
        if output_path:
            output_file = open(output_path, "w", newline="", encoding="utf-8")
        else:
            output_file = sys.stdout
        writer = csv.writer(output_file)
        writer.writerow(headers)
        return writer, output_file

    def _build_row(
        self,
        *,
        product: Product,
        variant: Variant,
        locale: Locale,
        channel: Channel,
        attributes: Sequence[Attribute],
        product_pavs: Dict[int, ProductAttributeValue],
        variant_pavs: Dict[int, ProductAttributeValue],
        value_i18n_map: Dict[int, str],
    ) -> List[str]:
        try:
            title_result = render_title(variant=variant, locale=locale, channel=channel)
            title = title_result.title
        except TitleRenderError as exc:
            title = f"[title_error] {exc}"

        row = [
            str(product.id),
            product.code or "",
            str(variant.id),
            variant.sku or "",
            product.product_type.code,
            locale.code,
            channel.code,
            title,
        ]

        for attr in attributes:
            pav = variant_pavs.get(attr.id) or product_pavs.get(attr.id)
            row.append(self._format_pav_value(pav, value_i18n_map) if pav else "")
        return row

    def _format_pav_value(
        self,
        pav: Optional[ProductAttributeValue],
        value_i18n_map: Dict[int, str],
    ) -> str:
        if not pav:
            return ""
        if pav.attribute_value_id:
            label = value_i18n_map.get(pav.attribute_value_id)
            return label or pav.attribute_value.code or ""

        if pav.value_text not in (None, ""):
            return str(pav.value_text)
        if pav.value_number is not None:
            text = str(pav.value_number.normalize()) if hasattr(pav.value_number, "normalize") else str(pav.value_number)
            return f"{text} {pav.unit}".strip() if pav.unit else text
        if pav.value_bool is not None:
            return "true" if pav.value_bool else "false"
        if pav.value_json is not None:
            return str(pav.value_json)
        return ""
