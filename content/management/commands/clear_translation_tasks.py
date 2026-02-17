"""Delete all translation tasks so you can run them again."""
from django.core.management.base import BaseCommand

from content.models import TranslationTask


class Command(BaseCommand):
    help = "Delete all TranslationTask rows so you can re-run translations."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only show how many would be deleted.",
        )

    def handle(self, *args, **options):
        qs = TranslationTask.objects.all()
        count = qs.count()
        if options["dry_run"]:
            self.stdout.write(self.style.WARNING(f"Would delete {count} translation task(s)."))
            return
        qs.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {count} translation task(s)."))
