from django.core.management.base import BaseCommand, CommandError
import json

from catalog.models import Product, Variant
from content.models import Locale
from pub.models import Channel
from kw.models import PlannerRun
from pub.services.title_renderer import TitleApprovalRequired, TitleRenderError, save_generation


class Command(BaseCommand):
    help = "Generate deterministic titles for variants of a product and persist GenerationOutput records."

    def add_arguments(self, parser):
        parser.add_argument("--product", type=int, required=True, help="Product ID to generate titles for")
        parser.add_argument("--locale", required=True, help="Locale code, e.g. de-DE")
        parser.add_argument("--channel", required=True, help="Channel code, e.g. shopify")
        parser.add_argument("--run", type=int, default=None, help="PlannerRun id to drive keyword selection")
        parser.add_argument("--run-id", dest="run", type=int, default=None, help="PlannerRun id to drive keyword selection")
        parser.add_argument(
            "--include-descriptions",
            action="store_true",
            help="Allow hook selection from description matches.",
        )
        parser.add_argument(
            "--variant",
            type=int,
            default=None,
            help="Optional variant ID to generate only for that variant of the product",
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Print detailed title resolution steps.",
        )

    def handle(self, *args, **options):
        product_id = options["product"]
        locale_code = options["locale"]
        channel_code = options["channel"]
        variant_id = options.get("variant")
        run_id = options.get("run")
        include_descriptions = options.get("include_descriptions")
        debug = options.get("debug")

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist as exc:
            raise CommandError(f"Product {product_id} not found") from exc

        try:
            locale = Locale.objects.get(code=locale_code)
        except Locale.DoesNotExist as exc:
            raise CommandError(f"Locale {locale_code} not found") from exc

        try:
            channel = Channel.objects.get(code=channel_code)
        except Channel.DoesNotExist as exc:
            raise CommandError(f"Channel {channel_code} not found") from exc

        run = None
        if run_id:
            try:
                run = PlannerRun.objects.get(id=run_id)
            except PlannerRun.DoesNotExist as exc:
                raise CommandError(f"PlannerRun {run_id} not found") from exc

        variants_qs = product.variants.all()
        if variant_id:
            variants_qs = variants_qs.filter(id=variant_id)

        if not variants_qs.exists():
            self.stdout.write(self.style.WARNING("No variants to process"))
            return

        successes = 0
        pending = 0
        errors = []
        for variant in variants_qs:
            try:
                output, _ = save_generation(
                    variant=variant,
                    locale=locale,
                    channel=channel,
                    run=run,
                    include_descriptions=include_descriptions,
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Variant {variant.id} -> {output.text} (run_id={output.run_id}, output_id={output.id})"
                    )
                )
                if debug:
                    self.stdout.write(
                        json.dumps(
                            output.score_json or {},
                            ensure_ascii=False,
                            indent=2,
                        )
                    )
                successes += 1
            except TitleApprovalRequired as exc:
                pending += 1
                preview = f" preview={exc.preview_title}" if exc.preview_title else ""
                selection = f" selection_id={exc.selection_id}" if exc.selection_id else ""
                self.stdout.write(
                    self.style.WARNING(f"Variant {variant.id}: needs approval{selection}{preview}")
                )
            except TitleRenderError as exc:
                errors.append((variant.id, str(exc)))
                self.stdout.write(self.style.ERROR(f"Variant {variant.id}: {exc}"))

        self.stdout.write(f"Done. Successes: {successes}, Pending: {pending}, Errors: {len(errors)}")
        if errors:
            for vid, err in errors:
                self.stdout.write(f"- Variant {vid}: {err}")
