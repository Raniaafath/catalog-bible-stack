from __future__ import annotations

from typing import List, Optional, Tuple

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalog.models import Product, ProductType
from content.models import Locale, ProductTypeI18n, ProductTypeSynonym, SynonymStatus, Channel
from kw.management.commands.parse_keywords import _normalize_term
from kw.models import Candidate, Keyword, PlannerRun


def _head_terms(pt: ProductType, locale: Locale, channel: Optional[Channel]) -> List[str]:
    """
    Collect the main label plus approved+active synonyms for this product type/locale/channel.
    Channel-specific synonyms win over channel-null when duplicates exist.
    """
    seen = set()
    terms: List[Tuple[int, str]] = []

    pti18n = ProductTypeI18n.objects.filter(product_type=pt, locale=locale).first()
    if pti18n and pti18n.label:
        norm = _normalize_term(pti18n.label)
        if norm and norm not in seen:
            seen.add(norm)
            terms.append((100, pti18n.label))

    syn_qs = ProductTypeSynonym.objects.filter(
        product_type=pt,
        locale=locale,
        status=SynonymStatus.APPROVED,
        is_active=True,
    ).order_by("-channel", "-priority", "-score", "-updated_at")
    if channel:
        syn_qs = syn_qs.filter(channel__in=[channel.id, None])
    for syn in syn_qs:
        norm = _normalize_term(syn.term)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        priority = 80 + (syn.priority or 0)
        terms.append((priority, syn.term))

    # Sort by priority descending, keep order deterministic.
    terms.sort(key=lambda t: t[0], reverse=True)
    return [t for _, t in terms]


class Command(BaseCommand):
    help = (
        "Create HEAD candidates from product type label/synonyms for all products of the PlannerRun's product type.\n"
        "Role=HEAD, status=suggested, one candidate per product (per term)."
    )

    def add_arguments(self, parser):
        parser.add_argument("--run", type=int, required=True, help="PlannerRun id to source product_type/locale/channel.")
        parser.add_argument("--limit", type=int, default=1, help="Max head terms to keep per product (default 1).")
        parser.add_argument("--dry-run", action="store_true", help="Do not write to DB.")

    def handle(self, *args, **opts):
        run_id = opts["run"]
        limit = opts["limit"]
        dry = opts["dry_run"]

        run = PlannerRun.objects.select_related("locale", "channel", "product_type").filter(id=run_id).first()
        if not run:
            raise CommandError(f"PlannerRun {run_id} not found")
        if not run.product_type:
            raise CommandError("PlannerRun has no product_type; cannot select head candidates.")
        if not run.channel:
            raise CommandError("PlannerRun has no channel; Candidate uniqueness expects a channel.")

        head_terms = _head_terms(run.product_type, run.locale, run.channel)
        if not head_terms:
            self.stdout.write(self.style.WARNING("No product type label/synonym terms found; nothing to do."))
            return
        if limit:
            head_terms = head_terms[:limit]

        products = Product.objects.filter(product_type=run.product_type)
        if not products.exists():
            self.stdout.write(self.style.WARNING("No products found for this product type; nothing to do."))
            return

        created = 0
        with transaction.atomic():
            for product in products:
                for idx, term in enumerate(head_terms):
                    norm = _normalize_term(term)
                    if not norm:
                        continue
                    kw, _ = Keyword.objects.get_or_create(
                        locale=run.locale,
                        normalized_term=norm,
                        defaults={"term": term},
                    )
                    if kw.term != term:
                        kw.term = term
                        kw.save(update_fields=["term"])
                    if dry:
                        created += 1
                        continue
                    Candidate.objects.update_or_create(
                        locale=run.locale,
                        channel=run.channel,
                        keyword=kw,
                        role=Candidate.CandidateRole.HEAD,
                        product=product,
                        variant=None,
                        defaults={
                            "weight": 100 - idx,  # simple ordering weight
                            "status": Candidate.CandidateStatus.SUGGESTED,
                            "selected_by": "head_synonym",
                            "reason": f"pt_head from run={run.id}",
                        },
                    )
                    created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"{'Dry-run: ' if dry else ''}Created/updated {created} HEAD candidates "
                f"for product_type={run.product_type.code} locale={run.locale.code} channel={run.channel.code}"
            )
        )
