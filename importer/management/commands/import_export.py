from django.core.management.base import BaseCommand, CommandError

from importer.services import export_import


class Command(BaseCommand):
    help = "Export a ProductImport (rows + errors) to CSV or XLSX."

    def add_arguments(self, parser):
        parser.add_argument("--import-id", type=int, required=True)
        parser.add_argument("--format", choices=["csv", "xlsx"], default="xlsx")

    def handle(self, *args, **options):
        import_id = options["import_id"]
        fmt = options["format"]
        try:
            path = export_import(import_id=import_id, fmt=fmt)
        except Exception as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"Exported import_id={import_id} -> {path}"))
