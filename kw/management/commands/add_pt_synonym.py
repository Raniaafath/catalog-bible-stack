from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from catalog.models import ProductType
from content.models import Locale, ProductTypeSynonym
from pub.models import Channel


class Command(BaseCommand):
    help = "Add or update a ProductTypeSynonym for a given product_type/locale/channel."

    def add_arguments(self, parser):
        parser.add_argument("--product-type", required=True, help="ProductType code")
        parser.add_argument("--locale", required=True, help="Locale code, e.g. it")
        parser.add_argument("--channel", required=False, default=None, help="Channel code (optional)")
        parser.add_argument("--term", required=True, help="Synonym term to add/update")
        parser.add_argument(
            "--status",
            default=ProductTypeSynonym.Status.APPROVED,
            choices=[c[0] for c in ProductTypeSynonym.Status.choices],
            help="Synonym status (default approved)",
        )
        parser.add_argument("--priority", type=int, default=0, help="Priority (default 0)")
        parser.add_argument("--score", type=float, default=None, help="Optional score")
        parser.add_argument("--source", default="manual", help="Provenance/source label")

    def handle(self, *args, **opts):
        pt = self._get_product_type(opts["product_type"])
        locale = self._get_locale(opts["locale"])
        channel = self._get_channel(opts["channel"]) if opts["channel"] else None
        term = opts["term"].strip()

        defaults = {
            "status": opts["status"],
            "is_active": True,
            "priority": opts["priority"],
            "score": opts["score"],
            "source": opts["source"],
        }
        obj, created = ProductTypeSynonym.objects.update_or_create(
            product_type=pt,
            locale=locale,
            channel=channel,
            term=term,
            defaults=defaults,
        )
        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} ProductTypeSynonym id={obj.id} term='{term}'"))

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

    def _get_channel(self, code: str) -> Channel | None:
        if not code:
            return None
        try:
            return Channel.objects.get(code=code)
        except Channel.DoesNotExist as exc:
            raise CommandError(f"Channel {code} not found") from exc
