from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalog.models import ProductType
from content.models import Channel, Locale
from kw.services.seed_builder import build_seed_items, build_seeds, build_seeds_debug, persist_seeds


class Command(BaseCommand):
    help = "Build and refresh PlannerSeed rows for a product type / locale / channel."

    def add_arguments(self, parser):
        parser.add_argument("--product-type", required=True, help="ProductType code")
        parser.add_argument("--locale", required=True, help="Locale code, e.g. de-DE")
        parser.add_argument("--channel", required=True, help="Channel code, e.g. amazon")
        parser.add_argument("--max-seeds", type=int, default=8, help="Maximum seeds to keep active (default 8)")
        parser.add_argument("--debug", action="store_true", help="Print seed components for debugging")

    def handle(self, *args, **opts):
        pt = self._get_product_type(opts["product_type"])
        locale = self._get_locale(opts["locale"])
        channel = self._get_channel(opts["channel"])
        max_seeds = opts["max_seeds"]

        if opts["debug"]:
            from pprint import pprint

            debug = build_seeds_debug(locale=locale, product_type=pt, channel=channel, max_seeds=max_seeds)
            self.stdout.write(self.style.WARNING("Seed debug:"))
            pprint(debug)
            seeds = debug["final_seed_items"]
        else:
            seeds = build_seed_items(locale=locale, product_type=pt, channel=channel, max_seeds=max_seeds)
        if not seeds:
            raise CommandError("No seeds generated; nothing to persist.")

        with transaction.atomic():
            activated = persist_seeds(locale=locale, product_type=pt, channel=channel, terms=seeds)

        self.stdout.write(
            self.style.SUCCESS(
                f"Refreshed planner seeds for {pt.code} {locale.code} {channel.code}: {len(activated)} active"
            )
        )

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
