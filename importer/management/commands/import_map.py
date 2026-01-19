from django.core.management.base import BaseCommand, CommandError

from importer.services import map_import


class Command(BaseCommand):
    help = "Apply attribute mappings for a ProductImport."

    def add_arguments(self, parser):
        parser.add_argument("--import-id", type=int, required=True)

    def handle(self, *args, **options):
        import_id = options["import_id"]
        try:
            result = map_import(import_id=import_id)
        except Exception as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            self.style.SUCCESS(
                f"Mapped import_id={import_id} mapped={result.mapped} errors={result.errors}"
            )
        )
