from __future__ import annotations

from typing import Optional

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from catalog.models import ProductType
from content.models import Locale
from kw.models import PlannerRun, Source
from pub.models import Channel


class Command(BaseCommand):
    help = (
        "Run an end-to-end pipeline: import -> translations -> seeds -> keyword fetch/import -> "
        "parse/map -> promote -> select candidates -> generate/export."
    )

    def add_arguments(self, parser):
        parser.add_argument("--product-type", required=True, help="ProductType code for the pipeline scope.")
        parser.add_argument("--locale", required=True, help="Locale code for keywords/translations/exports.")
        parser.add_argument("--channel", required=True, help="Channel code for seeds/keywords/exports.")

        parser.add_argument("--import-xlsx", help="Optional Excel file path to import.")
        parser.add_argument("--import-locale", help="Locale for import labels (defaults to --locale).")
        parser.add_argument("--import-channel", help="Channel for import synonyms (defaults to --channel).")
        parser.add_argument("--import-limit", type=int, default=None, help="Limit number of imported rows.")

        parser.add_argument("--skip-translations", action="store_true", help="Skip enqueue/run translation tasks.")
        parser.add_argument("--translation-scopes", default="attribute,attribute_value,product_type")
        parser.add_argument("--translation-batch-size", type=int, default=100)
        parser.add_argument("--translation-task-limit", type=int, default=25)

        parser.add_argument("--skip-seeds", action="store_true", help="Skip refresh_planner_seeds.")
        parser.add_argument("--max-seeds", type=int, default=8)

        parser.add_argument(
            "--keyword-source",
            choices=["existing", "ads-csv", "ads-api"],
            default="existing",
            help="Keyword source for PlannerRun.",
        )
        parser.add_argument("--run-id", type=int, default=None, help="Existing PlannerRun id to reuse.")
        parser.add_argument("--kw-csv", help="Keyword CSV path for ads-csv source.")
        parser.add_argument("--kw-delimiter", default=",", help="CSV delimiter for ads-csv import.")
        parser.add_argument("--kw-source", default="google_ads", help="kw.Source code for ads-csv import.")
        parser.add_argument("--kw-month", default=None, help="Metric month for ads-csv (YYYY-MM-01).")

        parser.add_argument("--ads-customer-id", help="Google Ads customer id (no dashes).")
        parser.add_argument("--ads-language-id", type=int, help="Google Ads language constant id.")
        parser.add_argument("--ads-location-ids", help="Comma-separated geo target ids.")
        parser.add_argument("--ads-country", default=None, help="Country code, e.g. DE.")
        parser.add_argument("--ads-page-url", default=None, help="Optional URL seed for Google Ads.")
        parser.add_argument("--ads-config-path", default=None, help="Optional google-ads.yaml path.")
        parser.add_argument("--ads-limit", type=int, default=500, help="Max ideas to store from ads-api.")

        parser.add_argument("--skip-parse", action="store_true", help="Skip parse_keywords.")
        parser.add_argument("--parse-limit", type=int, default=None)
        parser.add_argument("--skip-map", action="store_true", help="Skip map_keywords.")
        parser.add_argument("--map-mode", choices=["rules", "ai"], default="rules")
        parser.add_argument("--map-limit", type=int, default=None)

        parser.add_argument("--skip-promote", action="store_true", help="Skip promote_am_synonyms.")
        parser.add_argument("--promote-limit", type=int, default=None)
        parser.add_argument("--promote-head-terms", default="")
        parser.add_argument("--promote-stopwords", default="")

        parser.add_argument("--skip-select-head", action="store_true", help="Skip select_head_candidates.")
        parser.add_argument("--head-limit", type=int, default=1)
        parser.add_argument("--skip-select-candidates", action="store_true", help="Skip select_candidates.")
        parser.add_argument("--candidate-limit", type=int, default=None)
        parser.add_argument(
            "--skip-refresh-synonyms",
            action="store_true",
            help="Skip kw_refresh_value_synonyms after candidate selection.",
        )

        parser.add_argument("--skip-export", action="store_true", help="Skip export_translated_titles.")
        parser.add_argument("--export-output", help="Optional CSV path for export.")
        parser.add_argument("--export-skip-translation", action="store_true")
        parser.add_argument("--limit-products", type=int, default=None)
        parser.add_argument("--limit-variants", type=int, default=None)

        parser.add_argument("--dry-run", action="store_true", help="Do not write for parse/map/promote/select/import.")

    def handle(self, *args, **opts):
        product_type_code = opts["product_type"]
        locale_code = opts["locale"]
        channel_code = opts["channel"]
        dry_run = opts["dry_run"]

        self._ensure_locale_channel(locale_code, channel_code)

        if opts["import_xlsx"]:
            self.stdout.write("Step: import products")
            call_command(
                "import_export_products_xlsx",
                path=opts["import_xlsx"],
                channel=opts["import_channel"] or channel_code,
                locale=opts["import_locale"] or locale_code,
                dry_run=dry_run,
                limit=opts["import_limit"],
            )

        ran_translations = False
        if not opts["skip_translations"]:
            self.stdout.write("Step: translations")
            call_command(
                "enqueue_missing_translations",
                locale=locale_code,
                scopes=opts["translation_scopes"],
                batch_size=opts["translation_batch_size"],
            )
            call_command("run_translation_tasks", locale=locale_code, limit=opts["translation_task_limit"])
            ran_translations = True

        if not opts["skip_seeds"]:
            self.stdout.write("Step: seeds")
            call_command(
                "refresh_planner_seeds",
                product_type=product_type_code,
                locale=locale_code,
                channel=channel_code,
                max_seeds=opts["max_seeds"],
            )

        run_id = self._resolve_run_id(
            product_type_code=product_type_code,
            locale_code=locale_code,
            channel_code=channel_code,
            opts=opts,
        )

        if not opts["skip_parse"]:
            self.stdout.write("Step: parse keywords")
            call_command(
                "parse_keywords",
                run=run_id,
                limit=opts["parse_limit"],
                dry_run=dry_run,
            )

        if not opts["skip_map"]:
            self.stdout.write("Step: map keywords")
            call_command(
                "map_keywords",
                run=run_id,
                mode=opts["map_mode"],
                limit=opts["map_limit"],
                dry_run=dry_run,
            )

        if not opts["skip_promote"]:
            self.stdout.write("Step: promote synonyms")
            call_command(
                "promote_am_synonyms",
                locale=locale_code,
                channel=channel_code,
                run=run_id,
                limit=opts["promote_limit"],
                dry_run=dry_run,
                head_terms=opts["promote_head_terms"],
                stopwords=opts["promote_stopwords"],
            )

        if not opts["skip_select_head"]:
            self.stdout.write("Step: select head candidates")
            call_command(
                "select_head_candidates",
                run=run_id,
                limit=opts["head_limit"],
                dry_run=dry_run,
            )

        if not opts["skip_select_candidates"]:
            self.stdout.write("Step: select candidates")
            call_command(
                "select_candidates",
                run=run_id,
                limit=opts["candidate_limit"],
                dry_run=dry_run,
            )

        if not opts["skip_refresh_synonyms"]:
            self.stdout.write("Step: refresh value synonyms")
            call_command(
                "kw_refresh_value_synonyms",
                run_id=run_id,
                locale=locale_code,
                channel=channel_code,
            )

        if not opts["skip_export"]:
            self.stdout.write("Step: export titles")
            export_skip_translation = opts["export_skip_translation"] or ran_translations
            call_command(
                "export_translated_titles",
                locale=locale_code,
                channel=channel_code,
                product_type_code=product_type_code,
                limit_products=opts["limit_products"],
                limit_variants=opts["limit_variants"],
                output=opts["export_output"],
                skip_translation=export_skip_translation,
            )

        self.stdout.write(self.style.SUCCESS(f"Pipeline done (run_id={run_id})."))

    def _resolve_run_id(self, *, product_type_code: str, locale_code: str, channel_code: str, opts) -> int:
        keyword_source = opts["keyword_source"]
        run_id = opts["run_id"]

        if keyword_source == "existing":
            if not run_id:
                raise CommandError("--run-id is required when --keyword-source=existing")
            return run_id

        if keyword_source == "ads-csv":
            if not opts["kw_csv"]:
                raise CommandError("--kw-csv is required when --keyword-source=ads-csv")
            if not run_id:
                run_id = self._create_csv_run(
                    product_type_code=product_type_code,
                    locale_code=locale_code,
                    channel_code=channel_code,
                    source_code=opts["kw_source"],
                )
            self.stdout.write("Step: import keyword CSV")
            call_command(
                "kw_import_ads_keywords",
                csv=opts["kw_csv"],
                locale=locale_code,
                channel=channel_code,
                source=opts["kw_source"],
                run_id=run_id,
                month=opts["kw_month"],
                delimiter=opts["kw_delimiter"],
            )
            return run_id

        if keyword_source == "ads-api":
            required = ["ads_customer_id", "ads_language_id", "ads_location_ids"]
            missing = [key for key in required if not opts.get(key)]
            if missing:
                raise CommandError(f"Missing ads-api params: {', '.join(missing)}")
            started_at = timezone.now()
            self.stdout.write("Step: fetch keyword ideas")
            call_command(
                "fetch_keyword_ideas",
                product_type=product_type_code,
                locale=locale_code,
                channel=channel_code,
                country=opts["ads_country"],
                customer_id=opts["ads_customer_id"],
                language_id=opts["ads_language_id"],
                location_ids=opts["ads_location_ids"],
                page_url=opts["ads_page_url"],
                config_path=opts["ads_config_path"],
                limit=opts["ads_limit"],
            )
            run_id = self._latest_run_id(
                product_type_code=product_type_code,
                locale_code=locale_code,
                channel_code=channel_code,
                source_code="gads_keyword_planner",
                started_at=started_at,
            )
            if not run_id:
                raise CommandError("Could not resolve PlannerRun id after fetch_keyword_ideas.")
            return run_id

        raise CommandError(f"Unknown keyword source: {keyword_source}")

    def _create_csv_run(self, *, product_type_code: str, locale_code: str, channel_code: str, source_code: str) -> int:
        pt = self._get_product_type(product_type_code)
        locale = self._get_locale(locale_code)
        channel = self._get_channel(channel_code)
        source, _ = Source.objects.get_or_create(code=source_code)
        now = timezone.now()
        run = PlannerRun.objects.create(
            source=source,
            locale=locale,
            channel=channel,
            product_type=pt,
            status=PlannerRun.Status.SUCCESS,
            started_at=now,
            finished_at=now,
            request_json={"import": "ads_csv"},
        )
        return run.id

    def _latest_run_id(
        self,
        *,
        product_type_code: str,
        locale_code: str,
        channel_code: str,
        source_code: str,
        started_at,
    ) -> Optional[int]:
        run = (
            PlannerRun.objects.filter(
                created_at__gte=started_at,
                product_type__code=product_type_code,
                locale__code=locale_code,
                channel__code=channel_code,
                source__code=source_code,
            )
            .order_by("-created_at", "-id")
            .first()
        )
        return run.id if run else None

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

    def _ensure_locale_channel(self, locale_code: str, channel_code: str) -> None:
        Locale.objects.get_or_create(code=locale_code, defaults={"name": locale_code})
        Channel.objects.get_or_create(code=channel_code, defaults={"name": channel_code})
