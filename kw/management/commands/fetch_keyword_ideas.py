from __future__ import annotations

import json
from datetime import date
from typing import List

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from catalog.models import ProductType
from content.models import Channel, Locale
from kw.models import Keyword, Metric, PlannerRun, PlannerRunKeyword, PlannerRunSeed, PlannerSeed, Source
from kw.services.seed_builder import build_seed_items, build_seeds, persist_seeds
from kw.services.google_ads_keyword_planner import generate_keyword_ideas


def _month_start(year: int, month: int) -> date:
    return date(year, month, 1)


class Command(BaseCommand):
    help = "Fetch keyword ideas from Google Ads Keyword Planner and store PlannerRun/PlannerRunKeyword/Metric."

    def add_arguments(self, parser):
        parser.add_argument("--product-type", required=True, help="ProductType code/slug")
        parser.add_argument("--locale", required=True, help="Locale code (e.g., de-DE)")
        parser.add_argument("--country", required=False, default=None, help="Country code (e.g., DE)")
        parser.add_argument("--channel", required=True, help="Channel code (e.g., amazon, ebay)")

        parser.add_argument("--customer-id", required=True, help="Google Ads customer id (no dashes)")
        parser.add_argument("--language-id", required=True, type=int, help="Language constant ID (e.g., 1000 for German)")
        parser.add_argument(
            "--location-ids",
            required=True,
            help="Comma-separated geoTarget constant IDs (e.g., 2276 for DE).",
        )
        parser.add_argument("--page-url", default=None)
        parser.add_argument("--config-path", default=None, help="Optional google-ads.yaml path")
        parser.add_argument("--limit", type=int, default=500, help="Max ideas to store")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        pt = self._get_product_type(opts["product_type"])
        locale = self._get_locale(opts["locale"])
        channel = self._get_channel(opts["channel"])
        country_code = (opts["country"] or "").upper() or None
        source = self._get_source()

        location_ids = [int(x.strip()) for x in opts["location_ids"].split(",") if x.strip()]

        seed_terms = self._collect_seeds(locale=locale, product_type=pt, channel=channel)
        if not seed_terms and not opts["page_url"]:
            seed_items = build_seed_items(locale=locale, product_type=pt, channel=channel, max_seeds=8)
            if seed_items:
                persist_seeds(locale=locale, product_type=pt, channel=channel, terms=seed_items)
                seed_terms = [term for term, _typ in seed_items]
        if not seed_terms and not opts["page_url"]:
            raise CommandError("No PlannerSeed found/generated for this scope and no --page-url provided.")

        # Build seed list for the request and traceability
        used_seed_terms = seed_terms[:20]
        normalized_used = {" ".join(t.strip().lower().split()) for t in used_seed_terms if t}
        seed_qs = (
            PlannerSeed.objects.filter(locale=locale, normalized_term__in=normalized_used)
            .filter(
                (Q(product_type=pt) | Q(product_type__isnull=True)),
                (Q(channel=channel) | Q(channel__isnull=True)),
            )
            .order_by("-product_type_id", "-channel_id")
        )
        seed_items = [{"term": s.term, "seed_type": s.seed_type} for s in seed_qs]

        request_json = {
            "customer_id": opts["customer_id"],
            "language_id": opts["language_id"],
            "location_ids": location_ids,
            "seed_terms": seed_terms[:20],
            "page_url": opts["page_url"],
            "keyword_plan_network": "GOOGLE_SEARCH_AND_PARTNERS",
            "seed_items": seed_items,
        }

        if opts["dry_run"]:
            self.stdout.write(json.dumps(request_json, indent=2))
            return

        with transaction.atomic():
            run = PlannerRun.objects.create(
                source=source,
                locale=locale,
                channel=channel,
                product_type=pt,
                country_code=country_code,
                request_json=request_json,
                status=PlannerRun.Status.RUNNING,
            )

            for seed in seed_qs:
                PlannerRunSeed.objects.get_or_create(run=run, seed=seed)

            stored = 0
            for row in generate_keyword_ideas(
                customer_id=opts["customer_id"],
                language_constant_id=opts["language_id"],
                geo_target_constant_ids=location_ids,
                keyword_texts=seed_terms[:20],
                page_url=opts["page_url"],
                google_ads_config_path=opts["config_path"],
            ):
                if stored >= opts["limit"]:
                    break

                normalized = row.text.strip().lower()
                kw_obj, _ = Keyword.objects.get_or_create(
                    locale=locale,
                    normalized_term=normalized,
                    defaults={"term": row.text},
                )
                if kw_obj.term != row.text:
                    kw_obj.term = row.text
                    kw_obj.save(update_fields=["term"])

                prk, created = PlannerRunKeyword.objects.get_or_create(
                    run=run,
                    keyword=kw_obj,
                    defaults={
                        "seed": None,
                        "raw_json": {"avg_monthly_searches": row.avg_monthly_searches, "competition": row.competition},
                    },
                )
                if not created:
                    raw_json = prk.raw_json or {}
                    raw_json.update({"avg_monthly_searches": row.avg_monthly_searches, "competition": row.competition})
                    prk.raw_json = raw_json
                    prk.save(update_fields=["raw_json"])

                if row.monthly_volumes:
                    for (y, m, searches) in row.monthly_volumes:
                        Metric.objects.update_or_create(
                            keyword=kw_obj,
                            source=source,
                            month=_month_start(y, m),
                            planner_run=run,
                            defaults={
                                "avg_searches": searches,
                                "competition": None,
                                "cpc": None,
                                "raw_json": {"from": "keyword_plan", "year": y, "month": m},
                            },
                        )
                else:
                    Metric.objects.update_or_create(
                        keyword=kw_obj,
                        source=source,
                        month=date.today().replace(day=1),
                        planner_run=run,
                        defaults={
                            "avg_searches": row.avg_monthly_searches or 0,
                            "competition": None,
                            "cpc": None,
                            "raw_json": {"from": "keyword_plan"},
                        },
                    )

                stored += 1

            run.status = PlannerRun.Status.SUCCESS
            run.save(update_fields=["status"])

        self.stdout.write(self.style.SUCCESS(f"Created PlannerRun {run.id}, stored {stored} keyword ideas."))

    def _collect_seeds(self, *, locale: Locale, product_type: ProductType, channel: Channel) -> List[str]:
        seeds = (
            PlannerSeed.objects.filter(locale=locale, is_active=True)
            .filter(
                (Q(product_type=product_type) | Q(product_type__isnull=True)),
                (Q(channel=channel) | Q(channel__isnull=True)),
            )
            .order_by("-product_type_id", "-channel_id", "term")
        )
        ordered_terms: List[str] = []
        for seed in seeds:
            if seed.term and seed.term not in ordered_terms:
                ordered_terms.append(seed.term)
        return ordered_terms

    def _get_product_type(self, code: str) -> ProductType:
        try:
            return ProductType.objects.get(code=code)
        except ProductType.DoesNotExist as exc:
            raise CommandError(f"ProductType {code} not found") from exc

    def _get_locale(self, code: str) -> Locale:
        try:
            return Locale.objects.get(code=code)
        except Locale.DoesNotExist as exc:
            raise CommandError(f"Locale {code} not found") from exc

    def _get_channel(self, code: str) -> Channel:
        try:
            return Channel.objects.get(code=code)
        except Channel.DoesNotExist as exc:
            raise CommandError(f"Channel {code} not found") from exc

    def _get_source(self) -> Source:
        src, _ = Source.objects.get_or_create(code="gads_keyword_planner")
        return src
