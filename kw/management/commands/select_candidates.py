from __future__ import annotations

from typing import Dict, List, Set

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max

from catalog.models import Product, ProductAttributeValue
from kw.models import (
    AttributeMap,
    Candidate,
    Metric,
    PlannerRun,
    PlannerRunKeyword,
)


class Command(BaseCommand):
    help = (
        "Select keyword candidates for products of a PlannerRun's product type.\n"
        "Creates Candidate rows (role=hook) for approved AttributeMap entries whose attribute_value is present on the product."
    )

    def add_arguments(self, parser):
        parser.add_argument("--run", type=int, required=True, help="PlannerRun id to source keywords from.")
        parser.add_argument("--limit", type=int, default=None, help="Optional max number of candidates per product.")
        parser.add_argument("--dry-run", action="store_true", help="Do not write to DB.")

    def handle(self, *args, **opts):
        run_id = opts["run"]
        limit_per_product = opts["limit"]
        dry = opts["dry_run"]

        run = (
            PlannerRun.objects.select_related("locale", "channel", "product_type")
            .filter(id=run_id)
            .first()
        )
        if not run:
            raise CommandError(f"PlannerRun {run_id} not found")
        if not run.product_type:
            raise CommandError("PlannerRun has no product_type; cannot select candidates.")
        if not run.channel:
            raise CommandError("PlannerRun has no channel; Candidate uniqueness expects a channel.")

        # Collect approved attribute mappings tied to this run.
        attr_maps = (
            AttributeMap.objects.filter(origin_run_keyword__run=run, status=AttributeMap.Status.APPROVED)
            .select_related("keyword", "attribute_value", "attribute_value__attribute")
        )
        if not attr_maps.exists():
            self.stdout.write(self.style.WARNING("No approved AttributeMap entries for this run."))
            return

        # Precompute keyword volumes (max avg_searches across metrics).
        kw_ids = list(attr_maps.values_list("keyword_id", flat=True))
        kw_vols: Dict[int, int] = {
            row["keyword_id"]: row["vol"] or 0
            for row in Metric.objects.filter(keyword_id__in=kw_ids).values("keyword_id").annotate(vol=Max("avg_searches"))
        }

        products = Product.objects.filter(product_type=run.product_type)
        if not products.exists():
            self.stdout.write(self.style.WARNING("No products found for this product type; nothing to do."))
            return

        created = 0
        with transaction.atomic():
            for product in products:
                # Attribute values attached to this product (product-level only).
                pav_values: Set[int] = set(
                    ProductAttributeValue.objects.filter(product=product, attribute_value_id__isnull=False)
                    .values_list("attribute_value_id", flat=True)
                )
                if not pav_values:
                    continue

                # Pick mappings whose attribute_value is present on the product.
                product_maps: List[AttributeMap] = [m for m in attr_maps if m.attribute_value_id in pav_values]
                # Order by volume desc, then confidence desc to pick best first.
                product_maps.sort(
                    key=lambda m: (kw_vols.get(m.keyword_id, 0), float(m.confidence or 0)),
                    reverse=True,
                )
                if limit_per_product:
                    product_maps = product_maps[:limit_per_product]

                for amap in product_maps:
                    if dry:
                        created += 1
                        continue
                    Candidate.objects.update_or_create(
                        locale=run.locale,
                        channel=run.channel,
                        keyword=amap.keyword,
                        role=Candidate.CandidateRole.HOOK,
                        product=product,
                        variant=None,
                        defaults={
                            "weight": kw_vols.get(amap.keyword_id, 0),
                            "status": Candidate.CandidateStatus.SUGGESTED,
                            "selected_by": "select_candidates_rules",
                            "reason": f"attr={amap.attribute.code}; run={run.id}; confidence={amap.confidence}",
                        },
                    )
                    created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"{'Dry-run: ' if dry else ''}Selected {created} candidates for run {run_id} "
                f"product_type={run.product_type.code} channel={run.channel.code}"
            )
        )
