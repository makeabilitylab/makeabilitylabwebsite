import os
import logging

from django.core.management.base import BaseCommand

from website.models import Artifact, Talk, Poster, Publication

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Re-standardizes legacy talk/poster/publication filenames that were "
        "never renamed to the Author_TitleInTitleCase_VenueYear scheme (issue "
        "#1401). Production has many such rows (bulk-imported, so they never "
        "went through an authored Artifact.save()). This reuses the existing, "
        "now-correct rename path: when Artifact.do_filenames_need_updating() is "
        "True it calls artifact.save(), which renames the pdf_file, raw_file, "
        "and thumbnail on disk AND in the DB together. The original upload name "
        "is preserved (it was captured into original_*_filename by "
        "backfill_original_filenames / #1391 before this runs). Idempotent: "
        "once a row is standardized the check returns False, so re-runs do "
        "nothing. Safe to run on every container start."
    )

    # The concrete artifact models this covers. Posters are already
    # standardized in prod, but included for completeness/future data.
    MODELS = (Talk, Poster, Publication)

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be renamed without touching disk or DB.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        _logger.debug(
            f"Running restandardize_artifact_filenames.py (dry_run={dry_run}) "
            f"to rename legacy artifact files to the standardized scheme."
        )

        total_renamed = 0
        total_skipped = 0
        total_errors = 0
        for model in self.MODELS:
            renamed, skipped, errors = self._restandardize_model(model, dry_run)
            total_renamed += renamed
            total_skipped += skipped
            total_errors += errors

        verb = "Would rename" if dry_run else "Renamed"
        _logger.info(
            f"restandardize_artifact_filenames: {verb} {total_renamed} "
            f"artifact(s); skipped {total_skipped} (already standardized or no "
            f"usable name); {total_errors} row(s) errored and were skipped."
        )
        _logger.debug("Completed restandardize_artifact_filenames.py")

    def _restandardize_model(self, model, dry_run):
        """Re-standardize one concrete artifact model.

        Returns a ``(num_renamed, num_skipped, num_errors)`` tuple. Each row is
        processed inside its own try/except so a single malformed row (e.g. a
        null ``date``/``title``, which makes ``generate_filename`` raise via
        ``date.year`` / ``title.title()``) can't abort the batch and leave the
        rest of the dataset untouched. The entrypoint has no ``set -e``, so an
        aborted run would fail silently.
        """
        num_renamed = 0
        num_skipped = 0
        num_errors = 0
        # prefetch_related('authors') because the rename path reads the first
        # author's last name (generate_filename) and the rename only fires when
        # authors exist.
        for artifact in model.objects.prefetch_related("authors").all():
            try:
                if self._restandardize_row(artifact, dry_run):
                    num_renamed += 1
                else:
                    num_skipped += 1
            except Exception:
                _logger.exception(
                    "restandardize_artifact_filenames: skipping %s id=%s due to "
                    "an error", model.__name__, getattr(artifact, "pk", "?"),
                )
                num_errors += 1

        return num_renamed, num_skipped, num_errors

    def _restandardize_row(self, artifact, dry_run):
        """Re-standardize one artifact's files if needed.

        Returns True if it was (or would be) renamed, False if skipped. Raises
        on malformed data — the caller isolates that.
        """
        model_name = type(artifact).__name__

        # A standardized name needs an author, a title, and a date. Without
        # them generate_filename() can't produce a sensible name (and would
        # raise on null date/title), so leave the row untouched rather than
        # rename it to something degraded.
        if not artifact.title or not artifact.date:
            _logger.debug(
                f"Skipping {model_name} id={artifact.pk}: missing title/date."
            )
            return False
        if not artifact.authors.exists():
            # Artifact.save() only renames when authors exist (it needs the
            # first author's last name), so a save() here would be a no-op.
            _logger.debug(
                f"Skipping {model_name} id={artifact.pk}: no authors."
            )
            return False

        if not self._needs_restandardizing(artifact):
            return False

        if dry_run:
            new_name = Artifact.generate_filename(artifact)
            # Log the per-row preview at INFO (not DEBUG) so it is captured on
            # prod, where the file handler logs at INFO when DEBUG is off. This
            # is what makes the dry-run reviewable in prod's debug.log. The real
            # (non-dry-run) path below stays at DEBUG to avoid noise.
            _logger.info(
                f"[dry-run] Would re-standardize {model_name} id={artifact.pk} "
                f"to '{new_name}' (pdf='{artifact.pdf_file.name if artifact.pdf_file else None}', "
                f"raw='{artifact.raw_file.name if artifact.raw_file else None}')"
            )
            return True

        # Reuse the canonical rename path: save() renames pdf_file, raw_file,
        # and thumbnail on disk and in the DB, and leaves original_*_filename
        # untouched (it only captures on a new upload, not a no-update_fields
        # save), so the provenance recorded by #1391 is preserved.
        artifact.save()
        _logger.debug(
            f"Re-standardized {model_name} id={artifact.pk} to "
            f"'{Artifact.generate_filename(artifact)}'."
        )
        return True

    @staticmethod
    def _needs_restandardizing(artifact):
        """Whether the pdf_file/raw_file need standardizing, tolerant of the
        uniqueness suffix.

        This is NOT ``Artifact.do_filenames_need_updating``: that compares the
        basename to ``generate_filename`` for exact equality, so a file whose
        standardized name collided on disk and got a ``-<timestamp>`` suffix
        (``ensure_filename_is_unique``) reads as "needs updating" forever and
        would be re-renamed on every run — churning duplicate-name artifacts'
        filenames on every deploy. Here a name that equals the standardized
        base OR is a ``-<suffix>`` variant of it counts as already standardized,
        which keeps the command idempotent.
        """
        standardized = Artifact.generate_filename(artifact)
        for file_attr in ("pdf_file", "raw_file"):
            file_field = getattr(artifact, file_attr)
            if not file_field:
                continue
            current_no_ext = os.path.splitext(
                os.path.basename(file_field.name))[0]
            is_standardized = (
                current_no_ext == standardized
                or current_no_ext.startswith(standardized + "-")
            )
            if not is_standardized:
                return True
        return False
