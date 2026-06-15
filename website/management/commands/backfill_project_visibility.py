import logging
from django.core.management.base import BaseCommand
from website.models import Project

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "One-shot backfill of Project.is_visible for projects that predate the "
        "field (issue #1300). Legacy rows are added by the migration as NULL; "
        "this resolves each NULL to the project's previous public visibility "
        "using the old criteria (has a gallery image AND at least one "
        "publication). Idempotent: it only touches rows where is_visible IS "
        "NULL, so a manual admin choice (True or False) is never overwritten "
        "and it is safe to run on every container start."
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
            f"Running backfill_project_visibility.py (dry_run={dry_run}) to "
            f"resolve is_visible for legacy projects."
        )

        # Only projects that haven't had their visibility decided yet. New
        # projects are created with is_visible=False (private), so the only
        # NULLs are rows that existed before the column was added.
        candidates = Project.objects.filter(is_visible__isnull=True)

        num_visible = 0
        num_private = 0
        for project in candidates:
            # Legacy public-visibility criteria: a thumbnail AND a publication.
            should_be_visible = bool(project.gallery_image) and project.has_publication()

            if dry_run:
                _logger.debug(
                    f"[dry-run] Would set is_visible={should_be_visible} for "
                    f"project id={project.pk} '{project.name}'"
                )
            else:
                # Write via the queryset so this stays a pure data backfill and
                # does NOT trigger Project.save() (which auto-closes project
                # roles when end_date is set).
                Project.objects.filter(pk=project.pk).update(is_visible=should_be_visible)
                _logger.debug(
                    f"Set is_visible={should_be_visible} for project "
                    f"id={project.pk} '{project.name}'"
                )

            if should_be_visible:
                num_visible += 1
            else:
                num_private += 1

        verb = "Would resolve" if dry_run else "Resolved"
        _logger.info(
            f"backfill_project_visibility: {verb} {num_visible + num_private} "
            f"legacy project(s) — {num_visible} visible, {num_private} private."
        )
        _logger.debug("Completed backfill_project_visibility.py")
