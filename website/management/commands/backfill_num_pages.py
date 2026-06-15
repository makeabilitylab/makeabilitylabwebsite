import logging
from django.core.management.base import BaseCommand
from website.models import Publication
import website.utils.fileutils as ml_fileutils

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Backfills Publication.num_pages for existing publications that have a "
        "PDF but no page count, by reading the page count directly from the PDF "
        "(issue #1298). Only fills empty values, so manually entered counts are "
        "never overwritten. Idempotent: once a publication has a count it is "
        "skipped, so this is safe to run on every container start."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without writing to the database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        _logger.debug(
            f"Running backfill_num_pages.py (dry_run={dry_run}) to populate "
            f"num_pages for publications missing it."
        )

        # Only publications that have a PDF but no page count yet.
        candidates = Publication.objects.filter(
            num_pages__isnull=True
        ).exclude(pdf_file="").exclude(pdf_file__isnull=True)

        num_updated = 0
        num_skipped = 0
        for pub in candidates:
            page_count = ml_fileutils.get_pdf_page_count(pub.pdf_file)
            if not page_count:
                # Couldn't read the PDF (missing on disk, corrupt, etc.).
                # Leave num_pages empty and move on.
                _logger.debug(
                    f"Skipping pub id={pub.pk} '{pub.title}': could not determine "
                    f"page count from {pub.pdf_file.name}"
                )
                num_skipped += 1
                continue

            if dry_run:
                _logger.debug(
                    f"[dry-run] Would set num_pages={page_count} for pub "
                    f"id={pub.pk} '{pub.title}'"
                )
            else:
                # Write directly via the queryset so this stays a pure data
                # backfill — no thumbnail regeneration or file-rename side
                # effects from the model's save().
                Publication.objects.filter(pk=pub.pk).update(num_pages=page_count)
                _logger.debug(
                    f"Set num_pages={page_count} for pub id={pub.pk} '{pub.title}'"
                )
            num_updated += 1

        verb = "Would update" if dry_run else "Updated"
        _logger.info(
            f"backfill_num_pages: {verb} {num_updated} publication(s); "
            f"skipped {num_skipped} (PDF unreadable/missing)."
        )
        _logger.debug("Completed backfill_num_pages.py")
