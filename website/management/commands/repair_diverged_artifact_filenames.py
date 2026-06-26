import os
import logging

from django.core.management.base import BaseCommand

from website.models import Artifact, Talk, Poster, Publication

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)


# Map a file extension to the magic-byte signature we expect its content to
# start with. Used to disambiguate orphaned files that the bug renamed WITHOUT
# extensions (so we can't tell pdf from pptx from the name alone). Returns None
# for extensions we can't verify, in which case we refuse to guess.
def _expected_kind_for_ext(ext):
    ext = ext.lower()
    if ext == ".pdf":
        return "pdf"
    if ext in (".pptx", ".docx", ".key", ".zip"):
        return "zip"  # modern Office / Keynote / zip-based formats
    if ext in (".ppt", ".doc"):
        return "ole"  # legacy OLE compound formats
    return None


def _sniff_kind(path):
    """Best-effort content type of a file from its leading magic bytes."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(8)
    except OSError:
        return None
    if head.startswith(b"%PDF"):
        return "pdf"
    if head.startswith(b"PK\x03\x04"):
        return "zip"
    if head.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if head.startswith(b"\xd0\xcf\x11\xe0"):
        return "ole"
    return None


class Command(BaseCommand):
    help = (
        "Repairs artifacts whose pdf_file/raw_file row points at a file that no "
        "longer exists on disk because a rename moved it but the save() never "
        "committed (the #1390 dotted-name bug: a name like '...Dr.SangMook2009' "
        "made os.path.splitext eat the extension, the file was renamed "
        "extension-less on disk, and thumbnail generation then raised before "
        "super().save()). The file CONTENT is safe on disk under the malformed "
        "name; this finds that orphan (by matching the standardized base and "
        "confirming its content type, since the orphan has no usable "
        "extension), renames it to the correct standardized name, and repoints "
        "the DB. Divergence-gated and idempotent: a row whose files already "
        "exist on disk is skipped, so this is a safe no-op once repaired. Run "
        "with --dry-run first to review exactly what it would touch."
    )

    MODELS = (Talk, Poster, Publication)

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be repaired without touching disk or DB.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        _logger.info(
            f"Running repair_diverged_artifact_filenames (dry_run={dry_run})."
        )

        repaired = unrecoverable = 0
        for model in self.MODELS:
            for artifact in model.objects.prefetch_related("authors").all():
                result = self._repair_artifact(artifact, dry_run)
                repaired += result["repaired"]
                unrecoverable += result["unrecoverable"]

        verb = "Would repair" if dry_run else "Repaired"
        _logger.info(
            f"repair_diverged_artifact_filenames: {verb} {repaired} file(s); "
            f"{unrecoverable} diverged file(s) could not be matched to an "
            f"orphan on disk and were left untouched."
        )

    def _repair_artifact(self, artifact, dry_run):
        model_name = type(artifact).__name__
        repaired = unrecoverable = 0
        fixed_any = False

        for field_name in ("pdf_file", "raw_file"):
            file_field = getattr(artifact, field_name)
            if not file_field:
                continue
            # Only act on a true divergence: the DB names a file that is gone.
            if file_field.storage.exists(file_field.name):
                continue

            outcome = self._repair_field(artifact, field_name, dry_run)
            if outcome == "repaired":
                repaired += 1
                fixed_any = True
            elif outcome == "unrecoverable":
                unrecoverable += 1
                _logger.warning(
                    f"{model_name} id={artifact.pk}: {field_name} points at "
                    f"missing '{file_field.name}' and no matching orphan was "
                    f"found on disk; left untouched for manual review."
                )

        # If we repointed any files for real, persist + regenerate the thumbnail
        # via a normal save(). With the extension bug fixed the names are already
        # standardized, so save() does no further renaming; it just writes the
        # corrected field names and rebuilds the (now-missing) thumbnail.
        if fixed_any and not dry_run:
            artifact.save()

        return {"repaired": repaired, "unrecoverable": unrecoverable}

    def _repair_field(self, artifact, field_name, dry_run):
        """Locate the orphaned file for one diverged field and fix it.

        Returns "repaired", "unrecoverable", or "noop".
        """
        model_name = type(artifact).__name__
        file_field = getattr(artifact, field_name)

        # The extension is still correct in the (stale) DB name; the standardized
        # base comes from generate_filename. Together they form the correct name.
        ext = os.path.splitext(file_field.name)[1]
        correct_base = Artifact.generate_filename(artifact)
        # get_valid_filename is applied by the rename path; mirror it so our
        # on-disk comparisons match what the buggy rename actually wrote.
        from django.utils.text import get_valid_filename
        valid_base = get_valid_filename(correct_base)
        correct_basename = get_valid_filename(correct_base + ext)

        directory = os.path.dirname(file_field.path)
        rel_dir = os.path.dirname(file_field.name)
        if not os.path.isdir(directory):
            return "unrecoverable"

        expected_kind = _expected_kind_for_ext(ext)

        # Candidate orphans: the bug wrote the file as the (extension-less) valid
        # base, possibly with a "-<timestamp>" uniqueness suffix from colliding
        # with the sibling files. Match those, then confirm by content type so we
        # never mis-pair a pdf with a pptx/thumbnail (they share the base name).
        candidates = []
        for entry in os.listdir(directory):
            if entry == valid_base or entry.startswith(valid_base + "-"):
                full = os.path.join(directory, entry)
                if os.path.isfile(full):
                    candidates.append(entry)

        matches = [
            c for c in candidates
            if expected_kind is not None
            and _sniff_kind(os.path.join(directory, c)) == expected_kind
        ]

        if len(matches) != 1:
            _logger.debug(
                f"{model_name} id={artifact.pk}: {field_name} expected kind="
                f"{expected_kind}; candidates={candidates}; content-matches="
                f"{matches} (need exactly 1)."
            )
            return "unrecoverable"

        orphan = matches[0]
        target_full = os.path.join(directory, correct_basename)
        target_rel = os.path.join(rel_dir, correct_basename)

        _logger.info(
            f"[{'dry-run' if dry_run else 'apply'}] {model_name} "
            f"id={artifact.pk}: {field_name} '{file_field.name}' (missing) -> "
            f"on-disk orphan '{orphan}' renamed to '{correct_basename}' and "
            f"repointed."
        )

        if dry_run:
            return "repaired"

        # If the target name is somehow already taken by a different file, don't
        # clobber it — bail out for manual review.
        if os.path.exists(target_full) and orphan != correct_basename:
            _logger.warning(
                f"{model_name} id={artifact.pk}: target '{correct_basename}' "
                f"already exists; not overwriting. Left for manual review."
            )
            return "unrecoverable"

        os.rename(os.path.join(directory, orphan), target_full)
        # Persist the corrected name directly with update() rather than relying
        # on the caller's save(): save() may set update_fields=['thumbnail'] when
        # it rebuilds the stale thumbnail, which would drop a pdf_file/raw_file
        # write. update() guarantees the repointed name lands in the DB. We also
        # set it in memory so the caller's save() regenerates the thumbnail from
        # the now-correct pdf path.
        type(artifact).objects.filter(pk=artifact.pk).update(
            **{field_name: target_rel}
        )
        file_field.name = target_rel
        return "repaired"
