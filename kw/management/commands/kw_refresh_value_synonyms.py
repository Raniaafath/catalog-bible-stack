from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from content.models import AttributeValueSynonym
from kw.models import AttributeMap, Metric, PlannerRun, PlannerRunKeyword


class Command(BaseCommand):
    help = "Promote Keyword Planner attribute mappings into AttributeValueSynonym records (suggested) scoped by locale/channel."

    def add_arguments(self, parser):
        parser.add_argument("--run-id", type=int, required=True, help="PlannerRun ID to source keywords from")
        parser.add_argument("--locale", required=True, help="Locale code, e.g. de-DE")
        parser.add_argument("--channel", required=True, help="Channel code, e.g. shopify")

    def handle(self, *args, **options):
        run_id = options["run_id"]
        locale_code = options["locale"]
        channel_code = options["channel"]

        try:
            run = PlannerRun.objects.select_related("locale", "channel").get(id=run_id)
        except PlannerRun.DoesNotExist as exc:
            raise CommandError(f"PlannerRun {run_id} not found") from exc

        if run.locale.code != locale_code:
            raise CommandError(f"PlannerRun locale {run.locale.code} does not match --locale {locale_code}")
        if not run.channel or run.channel.code != channel_code:
            raise CommandError(f"PlannerRun channel {run.channel.code if run.channel else 'None'} does not match --channel {channel_code}")

        keyword_ids = list(PlannerRunKeyword.objects.filter(run=run).values_list("keyword_id", flat=True))
        if not keyword_ids:
            self.stdout.write(self.style.WARNING("No keywords linked to this run"))
            return

        attr_maps = (
            AttributeMap.objects.filter(
                keyword_id__in=keyword_ids,
                status=AttributeMap.Status.APPROVED,
                attribute_value__isnull=False,
            )
            .select_related("keyword", "attribute_value")
            .order_by("id")
        )
        if not attr_maps:
            self.stdout.write(self.style.WARNING("No approved AttributeMap rows for this run"))
            return

        created = updated = skipped = 0
        for amap in attr_maps:
            term = self._proposed_term(amap)
            score = self._latest_metric_score(amap.keyword_id)
            defaults = {
                "source": "google_ads",
                "score": score,
                "reason": amap.reason or f"planner_run={run.id}",
                "keyword_id": amap.keyword_id,
            }
            obj, was_created = AttributeValueSynonym.objects.update_or_create(
                attribute_value=amap.attribute_value,
                locale=run.locale,
                channel=run.channel,
                term=term,
                defaults={**defaults, "status": AttributeValueSynonym.Status.SUGGESTED},
            )
            if not was_created and obj.status == AttributeValueSynonym.Status.APPROVED:
                # Keep manual approval; just refresh scores/source/keyword/reason.
                for field, value in defaults.items():
                    setattr(obj, field, value)
                obj.save(update_fields=list(defaults.keys()) + ["updated_at"])
            elif not was_created:
                for field, value in defaults.items():
                    setattr(obj, field, value)
                obj.status = AttributeValueSynonym.Status.SUGGESTED
                obj.save(update_fields=list(defaults.keys()) + ["status", "updated_at"])
            if was_created:
                created += 1
            else:
                updated += 1
        self.stdout.write(self.style.SUCCESS(f"Synonyms created: {created}, updated: {updated}, skipped: {skipped}"))

    def _latest_metric_score(self, keyword_id: int) -> float:
        metric = Metric.objects.filter(keyword_id=keyword_id).order_by("-month").first()
        return float(metric.avg_searches) if metric and metric.avg_searches is not None else 0.0

    def _proposed_term(self, amap: AttributeMap) -> str:
        """
        Prefer the token from reason (e.g., reason='token:schwarz') to avoid full keyword phrases as synonyms.
        Fallback to keyword.term.
        """
        reason = amap.reason or ""
        if reason.startswith("token:"):
            token = reason.split("token:", 1)[1].strip()
            if token:
                return token
        return amap.keyword.term
