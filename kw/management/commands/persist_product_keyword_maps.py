from __future__ import annotations

from typing import Dict

from contextlib import nullcontext

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max

from catalog.models import Product
from kw.models import Keyword, KeywordParse, Metric, PlannerRun, PlannerRunKeyword, ProductKeywordMap
from kw.services.product_keyword_mapper import product_keyword_matches_for_run


class Command(BaseCommand):
    help = "Persist per-product keyword maps for a PlannerRun (enum + text matches)."

    def add_arguments(self, parser):
        parser.add_argument("--run", type=int, required=True, help="PlannerRun id.")
        parser.add_argument("--product-id", type=int, default=None, help="Limit to a single product id.")
        parser.add_argument("--limit", type=int, default=None, help="Optional limit of products.")
        parser.add_argument("--min-confidence", type=float, default=None, help="Optional min confidence for enum maps.")
        parser.add_argument("--no-text", action="store_true", help="Disable text value matching.")
        parser.add_argument("--no-i18n", action="store_true", help="Disable i18n text values.")
        parser.add_argument(
            "--include-descriptions",
            action="store_true",
            help="Include product descriptions in text matching.",
        )
        parser.add_argument(
            "--max-description-chars",
            type=int,
            default=2000,
            help="Max description chars when include-descriptions is enabled.",
        )
        parser.add_argument(
            "--max-text-matches",
            type=int,
            default=60,
            help="Max text matches per product.",
        )
        parser.add_argument(
            "--max-enum-maps",
            type=int,
            default=120,
            help="Max enum maps per product.",
        )
        parser.add_argument("--use-llm", action="store_true", help="Use LLM for text matching.")
        parser.add_argument("--llm-max-keywords", type=int, default=80, help="Max keywords to send to LLM per product.")
        parser.add_argument("--dry-run", action="store_true", help="Do not write to DB.")

    def handle(self, *args, **opts):
        run_id = opts["run"]
        product_id = opts["product_id"]
        limit = opts["limit"]
        min_confidence = opts["min_confidence"]
        include_text = not opts["no_text"]
        include_i18n = not opts["no_i18n"]
        include_descriptions = opts["include_descriptions"]
        max_description_chars = opts["max_description_chars"]
        max_text_matches = opts["max_text_matches"]
        max_enum_maps = opts["max_enum_maps"]
        use_llm = opts["use_llm"]
        llm_max_keywords = opts["llm_max_keywords"]
        dry = opts["dry_run"]

        run = PlannerRun.objects.select_related("locale", "product_type").filter(id=run_id).first()
        if not run:
            raise CommandError(f"PlannerRun {run_id} not found")

        products = Product.objects.all()
        if run.product_type:
            products = products.filter(product_type=run.product_type)
        if product_id:
            products = products.filter(id=product_id)
        if limit:
            products = products[:limit]

        prk_list = list(PlannerRunKeyword.objects.filter(run=run).select_related("keyword"))
        keyword_ids = [prk.keyword_id for prk in prk_list]
        parse_map: Dict[int, list] = {}
        for row in (
            KeywordParse.objects.filter(keyword_id__in=keyword_ids)
            .values("keyword_id", "phrases")
            .order_by("keyword_id", "-updated_at")
        ):
            if row["keyword_id"] not in parse_map:
                parse_map[row["keyword_id"]] = list(row["phrases"] or [])
        keyword_vol_map = {
            row["keyword_id"]: row["vol"] or 0
            for row in Metric.objects.filter(keyword_id__in=keyword_ids)
            .values("keyword_id")
            .annotate(vol=Max("avg_searches"))
        }
        if max_description_chars is not None and max_description_chars <= 0:
            max_description_chars = None
        if max_text_matches is not None and max_text_matches <= 0:
            max_text_matches = None
        if max_enum_maps is not None and max_enum_maps <= 0:
            max_enum_maps = None

        total = 0
        created = 0
        updated = 0
        for product in products:
            total += 1
            res = product_keyword_matches_for_run(
                product_id=product.id,
                run=run,
                min_confidence=min_confidence,
                include_text_values=include_text,
                include_i18n=include_i18n,
                include_descriptions=include_descriptions,
                max_description_chars=max_description_chars,
                use_llm=use_llm,
                llm_max_keywords=llm_max_keywords,
                max_text_matches=max_text_matches,
                prk_list=prk_list,
                parse_map=parse_map,
                keyword_vol_map=keyword_vol_map,
            )
            enum_qs = res["enum_maps"]
            if max_enum_maps:
                enum_maps = list(enum_qs[:max_enum_maps])
            else:
                enum_maps = list(enum_qs)
            text_matches = list(res["text_matches"])

            keyword_ids = {item["keyword_id"] for item in text_matches}
            keyword_map: Dict[int, Keyword] = {kw.id: kw for kw in Keyword.objects.filter(id__in=keyword_ids)}

            ctx = transaction.atomic() if not dry else nullcontext()
            with ctx:
                for amap in enum_maps:
                    if dry:
                        created += 1
                        continue
                    obj, is_created = ProductKeywordMap.objects.update_or_create(
                        product=product,
                        keyword=amap.keyword,
                        run=run,
                        source=ProductKeywordMap.Source.ENUM,
                        defaults={
                            "attribute": amap.attribute,
                            "attribute_value": amap.attribute_value,
                            "confidence": amap.confidence,
                            "match_kind": ProductKeywordMap.Source.ENUM,
                            "evidence": {
                                "attribute_map_id": amap.id,
                                "reason_code": amap.reason_code,
                                "evidence": amap.evidence,
                            },
                        },
                    )
                    if is_created:
                        created += 1
                    else:
                        updated += 1

                for item in text_matches:
                    kw = keyword_map.get(item["keyword_id"])
                    if not kw:
                        continue
                    if dry:
                        created += 1
                        continue
                    raw_source = item.get("match_kind") or item.get("source") or ProductKeywordMap.Source.TEXT
                    valid_sources = {s.value for s in ProductKeywordMap.Source}
                    source = raw_source if isinstance(raw_source, str) and raw_source in valid_sources else ProductKeywordMap.Source.TEXT
                    if hasattr(source, "value"):
                        source = source.value
                    obj, is_created = ProductKeywordMap.objects.update_or_create(
                        product=product,
                        keyword=kw,
                        run=run,
                        source=source,
                        defaults={
                            "confidence": None,
                            "attribute_id": item.get("attribute_id"),
                            "attribute_value_id": item.get("attribute_value_id"),
                            "num_value": item.get("num_value"),
                            "num_unit": item.get("num_unit"),
                            "match_kind": item.get("match_kind") or item.get("source") or "",
                            "matched_text": item.get("matched_text") or "",
                            "evidence": {
                                "matched_phrase": item.get("matched_phrase"),
                                "model": item.get("model"),
                                "variant_id": item.get("variant_id"),
                            },
                        },
                    )
                    if is_created:
                        created += 1
                    else:
                        updated += 1
            self.stdout.write(
                f"Product {product.id}: enum={len(enum_maps)} text={len(text_matches)}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. products={total} created={created} updated={updated}{' (dry-run)' if dry else ''}"
            )
        )
