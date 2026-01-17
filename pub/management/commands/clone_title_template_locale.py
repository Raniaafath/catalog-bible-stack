from django.core.management.base import BaseCommand, CommandError

from catalog.models import ProductType
from content.models import Locale
from pub.models import Channel, Template, TemplatePart


class Command(BaseCommand):
    help = "Clone the latest active TITLE template from one locale to another for a product type + channel."

    def add_arguments(self, parser):
        parser.add_argument("--product-type", required=True, help="Product type code, e.g. receveur_douche")
        parser.add_argument("--channel", required=True, help="Channel code, e.g. shopify")
        parser.add_argument("--src-locale", required=True, help="Locale code to copy from, e.g. fr")
        parser.add_argument("--dst-locale", required=True, help="Locale code to copy to, e.g. it")
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite existing destination template parts instead of aborting.",
        )
        parser.add_argument(
            "--activate",
            action="store_true",
            help="Ensure destination template status is ACTIVE (default: keep/create as ACTIVE).",
        )

    def handle(self, *args, **options):
        pt_code = options["product_type"]
        channel_code = options["channel"]
        src_locale_code = options["src_locale"]
        dst_locale_code = options["dst_locale"]
        force = options["force"]
        activate = options["activate"] or True  # Default to activating the template

        try:
            product_type = ProductType.objects.get(code=pt_code)
        except ProductType.DoesNotExist as exc:
            raise CommandError(f"ProductType {pt_code} not found") from exc

        try:
            channel = Channel.objects.get(code=channel_code)
        except Channel.DoesNotExist as exc:
            raise CommandError(f"Channel {channel_code} not found") from exc

        try:
            src_locale = Locale.objects.get(code=src_locale_code)
        except Locale.DoesNotExist as exc:
            raise CommandError(f"Source locale {src_locale_code} not found") from exc

        dst_locale, _ = Locale.objects.get_or_create(code=dst_locale_code, defaults={"name": dst_locale_code})

        src_template = (
            Template.objects.filter(
                product_type=product_type,
                locale=src_locale,
                channel=channel,
                kind=Template.Kind.TITLE,
                status=Template.Status.ACTIVE,
            )
            .order_by("-version", "-id")
            .first()
        )
        if not src_template:
            raise CommandError("No active source TITLE template found for that product_type/channel/locale.")

        dest_template = (
            Template.objects.filter(
                product_type=product_type,
                locale=dst_locale,
                channel=channel,
                kind=Template.Kind.TITLE,
            )
            .order_by("-version", "-id")
            .first()
        )

        if dest_template and not force:
            self.stdout.write(
                self.style.WARNING(
                    f"Destination template already exists (id={dest_template.id}, status={dest_template.status}). Use --force to overwrite parts."
                )
            )
            return

        if not dest_template:
            dest_template = Template.objects.create(
                product_type=product_type,
                locale=dst_locale,
                channel=channel,
                kind=Template.Kind.TITLE,
                version=1,
                status=Template.Status.ACTIVE if activate else Template.Status.DRAFT,
            )
            self.stdout.write(self.style.SUCCESS(f"Created destination template {dest_template.id}"))
        elif activate and dest_template.status != Template.Status.ACTIVE:
            dest_template.status = Template.Status.ACTIVE
            dest_template.save(update_fields=["status"])
            self.stdout.write(self.style.SUCCESS(f"Activated destination template {dest_template.id}"))

        # Copy parts
        src_parts = TemplatePart.objects.filter(template=src_template).order_by("position", "id")
        for part in src_parts:
            part_obj, created = TemplatePart.objects.update_or_create(
                template=dest_template,
                position=part.position,
                defaults={
                    "part_type": part.part_type,
                    "attribute": part.attribute,
                    "keyword_role": part.keyword_role,
                    "literal_text": part.literal_text,
                    "required": part.required,
                    "fallback_text": part.fallback_text,
                },
            )
            action = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"{action} part #{part_obj.position} ({part_obj.part_type})"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Cloned template {src_template.id} -> {dest_template.id} for locale {dst_locale.code} (product_type={product_type.code}, channel={channel.code})"
            )
        )
