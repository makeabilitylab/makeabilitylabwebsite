import os
import logging

from django.core.management.base import BaseCommand

from website.models import Artifact, Talk, Poster, Publication

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Backfills Artifact.original_pdf_filename / original_raw_filename for "
        "existing talks, posters, and publications whose file was never renamed "
        "to the standardized scheme (issue #1391). Production has many such rows "
        "predating the auto-rename feature, so their on-disk filename still IS "
        "the original upload name and can be recovered. Rows whose file already "
        "matches the standardized scheme have lost their original name and are "
        "left blank. Only fills empty values, so it never overwrites a name "
        "already captured at upload time. Idempotent: safe to run on every "
        "container start."
    )

    # The concrete artifact models whose files this backfill covers.
    MODELS = (Talk, Poster, Publication)

    # (FileField attr, original-name field attr) pairs to backfill.
    FILE_FIELDS = (
        ('pdf_file', 'original_pdf_filename'),
        ('raw_file', 'original_raw_filename'),
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
            f"Running backfill_original_filenames.py (dry_run={dry_run}) to "
            f"recover original upload filenames for never-renamed artifacts."
        )

        total_updated = 0
        total_skipped = 0
        total_errors = 0
        for model in self.MODELS:
            updated, skipped, errors = self._backfill_model(model, dry_run)
            total_updated += updated
            total_skipped += skipped
            total_errors += errors

        verb = "Would update" if dry_run else "Updated"
        _logger.info(
            f"backfill_original_filenames: {verb} {total_updated} filename "
            f"field(s); skipped {total_skipped} (already standardized — original "
            f"name unrecoverable); {total_errors} row(s) errored and were skipped."
        )
        _logger.debug("Completed backfill_original_filenames.py")

    def _backfill_model(self, model, dry_run):
        """Backfill both file fields for one concrete artifact model.

        Returns a ``(num_updated, num_skipped, num_errors)`` tuple counting
        individual filename fields touched / deliberately left blank / skipped
        because the row raised.

        Each row is processed inside its own try/except: this iterates the
        whole production dataset, and a single malformed row (e.g. a null
        ``date`` or ``title`` makes ``generate_filename`` raise) must not abort
        the entire backfill and leave every later row untouched. The entrypoint
        has no ``set -e``, so an aborted run would fail silently (the traceback
        prints but startup continues) — this per-row isolation is defensive
        insurance against that.
        """
        num_updated = 0
        num_skipped = 0
        num_errors = 0
        for file_attr, original_attr in self.FILE_FIELDS:
            # Only rows that have a file but no captured original name yet.
            candidates = (
                model.objects.filter(**{f"{original_attr}__isnull": True})
                .exclude(**{file_attr: ""})
                .exclude(**{f"{file_attr}__isnull": True})
            )
            # generate_filename() reads the first author's last name, so prefetch
            # authors to avoid a per-row query.
            candidates = candidates.prefetch_related("authors")

            for artifact in candidates:
                try:
                    if self._backfill_row(model, artifact, file_attr,
                                          original_attr, dry_run):
                        num_updated += 1
                    else:
                        num_skipped += 1
                except Exception:
                    # Log and move on — never let one row kill the batch.
                    _logger.exception(
                        "backfill_original_filenames: skipping %s id=%s %s due "
                        "to an error", model.__name__,
                        getattr(artifact, "pk", "?"), file_attr,
                    )
                    num_errors += 1

        return num_updated, num_skipped, num_errors

    def _backfill_row(self, model, artifact, file_attr, original_attr, dry_run):
        """Backfill one (artifact, file field) pair.

        Returns True if the original name was (or would be) recorded, False if
        the row was deliberately skipped because its file is already
        standardized. Raises on malformed data — the caller isolates that.
        """
        file_field = getattr(artifact, file_attr)
        if not file_field:
            return False

        current_basename = os.path.basename(file_field.name)
        current_no_ext = os.path.splitext(current_basename)[0]
        standardized_no_ext = Artifact.generate_filename(artifact)

        # Treat the file as already-standardized when its name equals the
        # standardized scheme OR is a uniquified variant of it. When a
        # standardized name collides on disk, ensure_filename_is_unique()
        # (fileutils.py) appends "-<timestamp>" — e.g.
        # "Lee_Talk_CHI2021-1782399772.42.pdf" — so the on-disk name still
        # STARTS WITH the standardized base. Matching only on exact equality
        # would misread those as never-renamed and record the standardized+
        # suffix name as the "original" — a false positive.
        already_standardized = (
            current_no_ext == standardized_no_ext
            or current_no_ext.startswith(standardized_no_ext + "-")
        )
        if already_standardized:
            # Already renamed — the original upload name is gone.
            _logger.debug(
                f"Skipping {model.__name__} id={artifact.pk} {file_attr}="
                f"'{current_basename}': already standardized."
            )
            return False

        # Never renamed: the current on-disk name is the original.
        if dry_run:
            _logger.debug(
                f"[dry-run] Would set {original_attr}='{current_basename}' "
                f"for {model.__name__} id={artifact.pk} '{artifact.title}'"
            )
        else:
            # Write directly via the queryset so this stays a pure data
            # backfill — no file-rename / thumbnail side effects from the
            # model's save().
            model.objects.filter(pk=artifact.pk).update(
                **{original_attr: current_basename}
            )
            _logger.debug(
                f"Set {original_attr}='{current_basename}' for "
                f"{model.__name__} id={artifact.pk} '{artifact.title}'"
            )
        return True
