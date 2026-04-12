"""
Management command to process pending article extraction tasks.
Run with: python manage.py process_extractions
"""

import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.rssapp.models import ExtractionTask, Article
from apps.rssapp.utils import extract_article_content

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Process pending article extraction tasks"

    def add_arguments(self, parser):
        parser.add_argument(
            "--max-tasks",
            type=int,
            default=10,
            help="Maximum number of tasks to process in one run (default: 10)",
        )
        parser.add_argument(
            "--retry-failed",
            action="store_true",
            help="Also retry tasks in 'failed' status (up to max_retries)",
        )
        parser.add_argument(
            "--max-age-hours",
            type=int,
            default=24,
            help="Only process tasks created within the last N hours (default: 24)",
        )

    def handle(self, *args, **options):
        max_tasks = options["max_tasks"]
        retry_failed = options["retry_failed"]
        max_age_hours = options["max_age_hours"]

        cutoff_time = timezone.now() - timedelta(hours=max_age_hours)

        # Build query for pending tasks
        query = ExtractionTask.objects.filter(
            status="pending",
            created_at__gte=cutoff_time,
        ).select_related("article")

        if retry_failed:
            from django.db.models import Q

            query = ExtractionTask.objects.filter(
                Q(status="pending") | Q(status="failed", retry_count__lt=3),
                created_at__gte=cutoff_time,
            ).select_related("article")

        tasks = query[:max_tasks]

        if not tasks:
            self.stdout.write(self.style.SUCCESS("No extraction tasks to process"))
            return

        self.stdout.write(f"Processing {len(tasks)} extraction task(s)...")

        success_count = 0
        failed_count = 0
        skipped_count = 0

        for task in tasks:
            try:
                self._process_task(task)
                success_count += 1
            except Exception as e:
                failed_count += 1
                logger.error(
                    f"Error processing extraction task {task.article_id}",
                    exc_info=True,
                )
                self.stdout.write(
                    self.style.ERROR(f"Task {task.article_id} failed: {e}")
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Completed: {success_count} success, "
                f"{failed_count} failed, {skipped_count} skipped"
            )
        )

    def _process_task(self, task: ExtractionTask):
        """Process a single extraction task."""
        article = task.article

        # Check if article already has content
        if article.content and article.content.strip():
            task.status = "skipped"
            task.completed_at = timezone.now()
            task.save(update_fields=["status", "completed_at"])
            self.stdout.write(
                self.style.WARNING(
                    f"Article {article.id} already has content, skipping"
                )
            )
            return

        # Mark as processing
        task.status = "processing"
        task.started_at = timezone.now()
        task.save(update_fields=["status", "started_at"])

        # Attempt extraction
        try:
            result = extract_article_content(article.link)

            # Update article with extracted content
            article.content = result.get("content", "")
            article.content_source = result.get("source", "summary")
            extraction_status = result.get("status", "failed")

            if extraction_status == "success":
                article.extraction_status = "success"
            else:
                article.extraction_status = extraction_status  # "failed" or "skipped"

            article.extracted_at = timezone.now()
            article.save(
                update_fields=[
                    "content",
                    "content_source",
                    "extraction_status",
                    "extracted_at",
                ]
            )

            # Mark task as complete
            task.status = (
                extraction_status if extraction_status == "success" else "success"
            )
            task.completed_at = timezone.now()
            task.save(update_fields=["status", "completed_at"])

            self.stdout.write(
                self.style.SUCCESS(
                    f"Extracted article {article.id} ({extraction_status})"
                )
            )

        except Exception as e:
            # Handle extraction failure
            task.retry_count += 1
            task.error_message = str(e)[:500]  # Store error message (truncated)

            if task.retry_count >= task.max_retries:
                task.status = "failed"
                article.extraction_status = "failed"
                task.completed_at = timezone.now()
            else:
                # Reset to pending for retry
                task.status = "pending"

            task.save()
            article.save(update_fields=["extraction_status"])

            self.stdout.write(
                self.style.ERROR(
                    f"Failed extracting article {article.id} "
                    f"({task.retry_count}/{task.max_retries}): {e}"
                )
            )
