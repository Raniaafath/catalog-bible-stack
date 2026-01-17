import csv
import datetime
from pathlib import Path
from typing import Optional

from django.core.management.base import BaseCommand, CommandError

from content.models import Locale
from kw.models import Keyword, Metric, PlannerRun, PlannerRunKeyword, Source
from pub.models import Channel


class Command(BaseCommand):
    help = "Import Google Ads keyword CSV into Keyword/Metric and link to a PlannerRun."

    def add_arguments(self, parser):
        parser.add_argument("--csv", required=True, help="Path to the exported keyword CSV")
        parser.add_argument("--locale", required=True, help="Locale code, e.g. de-DE")
        parser.add_argument("--channel", required=True, help="Channel code, e.g. shopify")
        parser.add_argument(
            "--source",
            default="google_ads",
            help="Source code to use/create in kw.Source (default: google_ads)",
        )
        parser.add_argument(
            "--run-id",
            type=int,
            default=None,
            help="Existing PlannerRun ID to attach to. If omitted, a new run is created.",
        )
        parser.add_argument(
            "--month",
            default=None,
            help="Month for Metric (YYYY-MM-01). If omitted, uses current month start.",
        )
        parser.add_argument(
            "--delimiter",
            default=",",
            help="CSV delimiter (default ','). Use ';' for EU exports.",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv"])
        if not csv_path.exists():
            raise CommandError(f"CSV not found: {csv_path}")

        locale_code = options["locale"]
        channel_code = options["channel"]
        delimiter = options["delimiter"]
        month_str = options["month"]

        month = self._parse_month(month_str)

        locale = self._get_locale(locale_code)
        channel = self._get_channel(channel_code)
        source = self._get_source(options["source"])
        run = self._get_or_create_run(options["run_id"], source, locale, channel)

        created_kw = updated_kw = created_metric = updated_metric = linked = 0

        with csv_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            required_cols = ["Keyword", "Avg. monthly searches"]
            for col in required_cols:
                if col not in reader.fieldnames:
                    raise CommandError(f"Missing required column '{col}' in CSV")

            for row in reader:
                term = (row.get("Keyword") or "").strip()
                if not term:
                    continue
                avg_searches = self._parse_int(row.get("Avg. monthly searches"))
                competition = self._parse_decimal(row.get("Competition (indexed value)"))
                cpc_high = self._parse_decimal(row.get("Top of page bid (high range)"))
                cpc_low = self._parse_decimal(row.get("Top of page bid (low range)"))

                kw_obj, kw_created = Keyword.objects.get_or_create(
                    locale=locale,
                    normalized_term=term.lower(),
                    defaults={"term": term},
                )
                if not kw_created and kw_obj.term != term:
                    kw_obj.term = term
                    kw_obj.save(update_fields=["term"])
                created_kw += 1 if kw_created else 0
                updated_kw += 0 if kw_created else 1

                metric_defaults = {
                    "avg_searches": avg_searches,
                    "competition": competition,
                    "cpc": cpc_high or cpc_low,
                    "raw_json": {
                        "cpc_high": cpc_high,
                        "cpc_low": cpc_low,
                        "competition_index": competition,
                    },
                }
                metric, metric_created = Metric.objects.update_or_create(
                    keyword=kw_obj,
                    source=source,
                    month=month,
                    planner_run=run,
                    defaults=metric_defaults,
                )
                created_metric += 1 if metric_created else 0
                updated_metric += 0 if metric_created else 1

                _, link_created = PlannerRunKeyword.objects.get_or_create(run=run, keyword=kw_obj)
                linked += 1 if link_created else 0

        self.stdout.write(
            self.style.SUCCESS(
                f"Keywords created: {created_kw}, updated: {updated_kw}; "
                f"Metrics created: {created_metric}, updated: {updated_metric}; "
                f"Run links: {linked}. Run ID: {run.id}"
            )
        )

    def _parse_month(self, month_str: Optional[str]) -> datetime.date:
        if month_str:
            try:
                return datetime.datetime.strptime(month_str, "%Y-%m-%d").date()
            except ValueError as exc:
                raise CommandError("--month must be YYYY-MM-DD (use first of month)") from exc
        today = datetime.date.today()
        return today.replace(day=1)

    def _parse_int(self, value: Optional[str]) -> Optional[int]:
        if value is None or value == "":
            return None
        try:
            return int(str(value).replace(",", "").replace(".", ""))
        except ValueError:
            return None

    def _parse_decimal(self, value: Optional[str]) -> Optional[float]:
        if value is None:
            return None
        text = str(value).strip().replace('"', "")
        if text == "":
            return None
        text = text.replace(".", "").replace(",", ".")
        try:
            return float(text)
        except ValueError:
            return None

    def _get_locale(self, code: str):
        try:
            return Locale.objects.get(code=code)
        except Locale.DoesNotExist as exc:
            raise CommandError(f"Locale {code} not found") from exc

    def _get_channel(self, code: str):
        try:
            return Channel.objects.get(code=code)
        except Channel.DoesNotExist as exc:
            raise CommandError(f"Channel {code} not found") from exc

    def _get_source(self, code: str):
        src, _ = Source.objects.get_or_create(code=code)
        return src

    def _get_or_create_run(self, run_id: Optional[int], source, locale, channel):
        if run_id:
            try:
                return PlannerRun.objects.get(id=run_id)
            except PlannerRun.DoesNotExist as exc:
                raise CommandError(f"PlannerRun {run_id} not found") from exc
        return PlannerRun.objects.create(
            source=source,
            locale=locale,
            channel=channel,
            status=PlannerRun.Status.SUCCESS,
            started_at=datetime.datetime.utcnow(),
            finished_at=datetime.datetime.utcnow(),
            request_json={"import": "google_ads_csv"},
        )
