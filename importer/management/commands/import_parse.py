from django.core.management.base import BaseCommand, CommandError

from importer.services import parse_import


class Command(BaseCommand):
    help = "Parse a ProductImport file into ImportRow entries."

    def add_arguments(self, parser):
        parser.add_argument("--import-id", type=int, required=True)

    def handle(self, *args, **options):
        import_id = options["import_id"]
        try:
            result = parse_import(import_id=import_id)
        except Exception as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            self.style.SUCCESS(
                f"Parsed import_id={import_id} rows={result.total} ok={result.ok} errors={result.errors}"
            )
        )
