"""
Management command to process pending translation tasks.

This command uses the shared translation_processor service, which can also
be called directly from API views for automatic processing.
"""

from django.core.management.base import BaseCommand

from content.models import Locale, TranslationTask
from content.services.translation_processor import process_translation_task


class Command(BaseCommand):
    help = "Process pending TranslationTask rows and upsert i18n labels using OpenAI."

    def add_arguments(self, parser):
        parser.add_argument("--locale", required=True, help="Target locale code, e.g. en or de")
        parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="Max number of tasks to process in this run.",
        )
        parser.add_argument(
            "--task-id",
            type=int,
            help="Process a specific task by ID (ignores --locale and --limit).",
        )

    def handle(self, *args, **options):
        # If a specific task ID is provided, process just that task
        if options.get("task_id"):
            task_id = options["task_id"]
            self.stdout.write(f"Processing task {task_id}...")
            success = process_translation_task(task_id)
            if success:
                self.stdout.write(self.style.SUCCESS(f"Task {task_id} completed successfully"))
            else:
                self.stdout.write(self.style.ERROR(f"Task {task_id} failed"))
            return

        # Otherwise, process pending tasks for the given locale
        target_locale_code = options["locale"]
        limit = options["limit"]

        target_locale, _ = Locale.objects.get_or_create(
            code=target_locale_code, 
            defaults={"name": target_locale_code}
        )

        tasks = (
            TranslationTask.objects.filter(
                locale=target_locale.code, 
                status=TranslationTask.Status.PENDING
            )
            .order_by("created_at")[:limit]
        )
        
        if not tasks:
            self.stdout.write(self.style.WARNING("No pending translation tasks"))
            return

        processed = 0
        failed = 0
        for task in tasks:
            self.stdout.write(f"Processing task {task.id} ({task.scope})...")
            success = process_translation_task(task.id)
            if success:
                processed += 1
                self.stdout.write(self.style.SUCCESS(f"  Task {task.id} completed"))
            else:
                failed += 1
                self.stdout.write(self.style.ERROR(f"  Task {task.id} failed"))

        self.stdout.write(
            self.style.SUCCESS(f"\nCompleted: {processed} tasks processed, {failed} failed")
        )
