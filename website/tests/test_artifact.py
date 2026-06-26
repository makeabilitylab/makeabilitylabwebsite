"""Tests for Artifact model methods (filename-drift check, raw-file label)."""

import os
from datetime import date
from unittest.mock import MagicMock, patch

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import SimpleTestCase

from website.models import Artifact, Publication, Talk
from website.tests.base import DatabaseTestCase
from website.tests.factories import TalkFactory


def _pdf(name):
    return SimpleUploadedFile(name, b"%PDF-1.4 test", content_type="application/pdf")


def _raw(name):
    return SimpleUploadedFile(name, b"PKstub", content_type="application/octet-stream")


# --- Artifact filename check regression -----------------------------------


class ArtifactFilenameUpdateCheckTests(SimpleTestCase):
    """
    Regression tests for Artifact.do_filenames_need_updating.

    The raw_file and thumbnail branches each compared against
    ``artifact.pdf_file.name`` (copy-pasted from the pdf_file branch)
    instead of ``artifact.raw_file.name`` / ``artifact.thumbnail.name``.
    The bug masked filename drift in those fields: when pdf_file matched
    but raw_file or thumbnail had a stale name, the function returned
    False instead of True. These tests pin the per-branch lookup.
    """

    def _patch_generate(self, value):
        return patch(
            "website.models.artifact.Artifact.generate_filename",
            return_value=value,
        )

    def test_all_matching_returns_false(self):
        from website.models.artifact import Artifact
        with self._patch_generate("Doe2020Title"):
            artifact = MagicMock()
            artifact.pdf_file = MagicMock()
            artifact.pdf_file.name = "publications/Doe2020Title.pdf"
            artifact.raw_file = MagicMock()
            artifact.raw_file.name = "publications/Doe2020Title.zip"
            artifact.thumbnail = MagicMock()
            artifact.thumbnail.name = "thumbnails/Doe2020Title.jpg"
            self.assertFalse(Artifact.do_filenames_need_updating(artifact))

    def test_raw_file_mismatch_when_pdf_file_matches(self):
        """
        Under the bug the raw_file branch looked at pdf_file.name (which
        matches) and returned False; the fix makes it look at
        raw_file.name and correctly report the mismatch.
        """
        from website.models.artifact import Artifact
        with self._patch_generate("Doe2020Title"):
            artifact = MagicMock()
            artifact.pdf_file = MagicMock()
            artifact.pdf_file.name = "publications/Doe2020Title.pdf"
            artifact.raw_file = MagicMock()
            artifact.raw_file.name = "publications/StaleName.zip"
            artifact.thumbnail = None
            self.assertTrue(Artifact.do_filenames_need_updating(artifact))

    def test_thumbnail_mismatch_when_pdf_file_matches(self):
        """Same shape as the raw_file regression, for the thumbnail branch."""
        from website.models.artifact import Artifact
        with self._patch_generate("Doe2020Title"):
            artifact = MagicMock()
            artifact.pdf_file = MagicMock()
            artifact.pdf_file.name = "publications/Doe2020Title.pdf"
            artifact.raw_file = None
            artifact.thumbnail = MagicMock()
            artifact.thumbnail.name = "thumbnails/StaleName.jpg"
            self.assertTrue(Artifact.do_filenames_need_updating(artifact))


class ArtifactRawFileLabelTests(SimpleTestCase):
    """
    Regression tests for Artifact.raw_file_label (issue #1152).

    The talk snippet previously hardcoded "PPTX" next to the raw_file
    download link, mislabeling .key (Keynote) and any other format. The
    label is derived from the file extension.
    """

    def _artifact_with_raw_file(self, name):
        from website.models.artifact import Artifact
        artifact = MagicMock(spec=Artifact)
        artifact.raw_file = MagicMock() if name else None
        if name:
            artifact.raw_file.name = name
        artifact.RAW_FILE_LABELS = Artifact.RAW_FILE_LABELS
        return artifact

    def _label(self, name):
        from website.models.artifact import Artifact
        return Artifact.raw_file_label.fget(self._artifact_with_raw_file(name))

    def test_pptx_label(self):
        self.assertEqual(self._label("talks/Doe2020Title.pptx"), "PPTX")

    def test_keynote_label(self):
        self.assertEqual(self._label("talks/Doe2020Title.key"), "Keynote")

    def test_ai_label(self):
        self.assertEqual(self._label("posters/Doe2020Title.ai"), "AI")

    def test_figma_label(self):
        self.assertEqual(self._label("talks/Doe2020Title.fig"), "Figma")

    def test_extension_case_insensitive(self):
        self.assertEqual(self._label("talks/Doe2020Title.PPTX"), "PPTX")
        self.assertEqual(self._label("talks/Doe2020Title.Key"), "Keynote")

    def test_unknown_extension_falls_back_to_uppercased_ext(self):
        self.assertEqual(self._label("talks/Doe2020Title.odp"), "ODP")

    def test_no_raw_file_returns_none(self):
        self.assertIsNone(self._label(None))

    def test_no_extension_returns_none(self):
        self.assertIsNone(self._label("talks/Doe2020Title"))


# --- Artifact.save() with no PDF ------------------------------------------


class ArtifactSaveNullPdfTests(DatabaseTestCase):
    """
    Regression test for Artifact.save() when ``pdf_file`` is empty (#1278).

    ``pdf_file`` is nullable (``null=True, default=None``), so an artifact can
    legitimately exist without a PDF. But the thumbnail-generation block in
    Artifact.save() ran ``os.path.basename(self.pdf_file.name)`` unconditionally
    on every non-first save -- and ``self.pdf_file.name`` is ``None`` when the
    field is empty, raising ``TypeError: expected str ... not NoneType``.

    Any second save of a PDF-less artifact triggered it: an admin edit, or the
    ``authors_changed`` m2m signal re-saving to rename files. This pins the
    guard so a missing PDF simply means "no thumbnail to generate".
    """

    def test_resaving_artifact_without_pdf_does_not_crash(self):
        pub = Publication.objects.create(title="No PDF", date=date(2024, 1, 1))
        # First save (objects.create) is fine; the crash was on the *second*.
        pub.location = "Seattle, WA"
        pub.save()  # must not raise
        self.assertFalse(bool(Publication.objects.get(pk=pub.pk).pdf_file))


# --- #1391: original uploaded filename capture ----------------------------


class OriginalFilenameCaptureTests(DatabaseTestCase):
    """
    Artifact.save() captures the human-recognizable upload name into
    ``original_pdf_filename`` / ``original_raw_filename`` before the
    standardized rename destroys it, but only on a *genuine new upload*
    (issue #1391).
    """

    def test_new_upload_captures_original_and_survives_rename(self):
        """
        On the initial upload the original names are snapshotted, and they
        survive the ``authors_changed`` rename pass that renames the files on
        disk to the standardized Author_Title_VenueYear scheme.
        """
        person = self.make_person(last_name="Zhang")
        talk = TalkFactory(
            title="My Cool Talk",
            forum_name="CHI",
            date=date(2024, 1, 1),
            pdf_file=_pdf("MyTalk_v3_final.pdf"),
            raw_file=_raw("MyTalk_v3_final.pptx"),
            authors=[person],
        )
        talk.refresh_from_db()

        # The original upload names are preserved...
        self.assertEqual(talk.original_pdf_filename, "MyTalk_v3_final.pdf")
        self.assertEqual(talk.original_raw_filename, "MyTalk_v3_final.pptx")
        # ...while the files on disk were renamed to the standardized scheme.
        self.assertIn("Zhang", os.path.basename(talk.pdf_file.name))
        self.assertNotIn("MyTalk_v3_final", os.path.basename(talk.pdf_file.name))

    def test_replacing_file_on_edit_updates_original(self):
        """
        Uploading a replacement file through an edit (the admin passes the
        changed field in ``update_fields``) re-captures the new upload name.
        """
        person = self.make_person(last_name="Zhang")
        talk = TalkFactory(
            title="My Cool Talk", forum_name="CHI", date=date(2024, 1, 1),
            pdf_file=_pdf("MyTalk_v3_final.pdf"), authors=[person],
        )

        talk.pdf_file = _pdf("Revised_v2_FINAL.pdf")
        talk.save(update_fields=["pdf_file"])
        talk.refresh_from_db()

        self.assertEqual(talk.original_pdf_filename, "Revised_v2_FINAL.pdf")

    def test_metadata_only_edit_does_not_clobber_original(self):
        """
        A later edit that does not touch the file (only metadata) must NOT
        overwrite the stored original with the now-standardized filename.
        """
        person = self.make_person(last_name="Zhang")
        talk = TalkFactory(
            title="My Cool Talk", forum_name="CHI", date=date(2024, 1, 1),
            pdf_file=_pdf("MyTalk_v3_final.pdf"), authors=[person],
        )

        talk.location = "Honolulu, HI"
        talk.save(update_fields=["location"])
        talk.refresh_from_db()

        self.assertEqual(talk.original_pdf_filename, "MyTalk_v3_final.pdf")


class BackfillOriginalFilenamesTests(DatabaseTestCase):
    """
    The backfill_original_filenames command recovers the original upload name
    for never-renamed artifacts (whose on-disk filename still IS the original),
    leaves already-standardized rows blank, and never overwrites a value that
    is already set (issue #1391).
    """

    def test_backfills_never_renamed_leaves_standardized_and_is_idempotent(self):
        # (a) Legacy never-renamed talk: created without authors, so save()
        # leaves the upload filename untouched. Then null the captured original
        # to simulate a row predating this feature.
        legacy = TalkFactory(
            title="Legacy Talk", forum_name="UIST", date=date(2020, 1, 1),
            pdf_file=_pdf("OldUpload_final.pdf"),
        )
        legacy_name = os.path.basename(legacy.pdf_file.name)
        Talk.objects.filter(pk=legacy.pk).update(original_pdf_filename=None)

        # (b) Standardized talk: created with an author, so save() renamed the
        # file to the Author_Title_VenueYear scheme. Null its original too.
        standard = TalkFactory(
            title="Standard Talk", forum_name="CHI", date=date(2021, 1, 1),
            pdf_file=_pdf("whatever_upload.pdf"),
            authors=[self.make_person(last_name="Lee")],
        )
        Talk.objects.filter(pk=standard.pk).update(original_pdf_filename=None)

        call_command("backfill_original_filenames")

        legacy.refresh_from_db()
        standard.refresh_from_db()
        # Never-renamed file: its current basename is recorded as the original.
        self.assertEqual(legacy.original_pdf_filename, legacy_name)
        # Already-standardized file: original is unrecoverable, left blank.
        self.assertIsNone(standard.original_pdf_filename)

        # Idempotent: a value already set is never overwritten (only nulls fill).
        Talk.objects.filter(pk=legacy.pk).update(
            original_pdf_filename="ManuallyCorrected.pdf"
        )
        call_command("backfill_original_filenames")
        legacy.refresh_from_db()
        self.assertEqual(legacy.original_pdf_filename, "ManuallyCorrected.pdf")

    def test_uniquified_standardized_name_is_not_backfilled(self):
        """
        When a standardized filename collided on disk, the rename appended a
        "-<timestamp>" suffix (ensure_filename_is_unique). Such a name is still
        a renamed file, NOT an original upload, so the backfill must leave it
        blank rather than recording the standardized+suffix name.
        """
        person = self.make_person(last_name="Park")
        talk = TalkFactory(
            title="Unique Talk", forum_name="CHI", date=date(2022, 1, 1),
            pdf_file=_pdf("anything.pdf"), authors=[person],
        )
        standardized = Artifact.generate_filename(talk)
        # Simulate the uniquified on-disk name and a not-yet-backfilled row.
        uniquified = f"talks/{standardized}-1782399772.42.pdf"
        Talk.objects.filter(pk=talk.pk).update(
            pdf_file=uniquified, original_pdf_filename=None
        )

        call_command("backfill_original_filenames")

        talk.refresh_from_db()
        self.assertIsNone(talk.original_pdf_filename)

    def test_one_bad_row_does_not_abort_the_batch(self):
        """
        The backfill runs on every container start over the whole dataset, so a
        single malformed row must not abort the run and leave every other row
        untouched. A null ``date`` makes ``generate_filename`` raise
        (``date.year``); before per-row isolation that exception propagated out
        of the command. Here the bad row is skipped and a good legacy row is
        still backfilled.
        """
        # Malformed: no authors (so save() skips the rename and accepts the
        # null date) + a file, which makes it a backfill candidate that raises.
        bad = TalkFactory(
            title="Bad Row", forum_name="CHI", date=None,
            pdf_file=_pdf("bad_upload.pdf"),
        )
        # A good legacy candidate with a non-standard (never-renamed) name.
        good = TalkFactory(
            title="Good Row", forum_name="CHI", date=date(2019, 1, 1),
            pdf_file=_pdf("good_upload_final.pdf"),
        )
        good_name = os.path.basename(good.pdf_file.name)
        Talk.objects.filter(pk__in=[bad.pk, good.pk]).update(
            original_pdf_filename=None
        )

        # Must not raise despite the malformed row...
        call_command("backfill_original_filenames")

        good.refresh_from_db()
        bad.refresh_from_db()
        # ...and the good row is still processed.
        self.assertEqual(good.original_pdf_filename, good_name)
        self.assertIsNone(bad.original_pdf_filename)


class OriginalUploadFilenamesDisplayTests(SimpleTestCase):
    """ArtifactAdmin.original_upload_filenames read-only display (issue #1391)."""

    def _render(self, pdf=None, raw=None):
        from website.admin.artifact_admin import ArtifactAdmin
        obj = MagicMock()
        obj.original_pdf_filename = pdf
        obj.original_raw_filename = raw
        # The method does not use self; pass None.
        return str(ArtifactAdmin.original_upload_filenames(None, obj))

    def test_shows_both_filenames(self):
        html = self._render(pdf="MyTalk_v3.pdf", raw="MyTalk_v3.pptx")
        self.assertIn("PDF", html)
        self.assertIn("MyTalk_v3.pdf", html)
        self.assertIn("Raw file", html)
        self.assertIn("MyTalk_v3.pptx", html)

    def test_pdf_only_omits_raw_row(self):
        html = self._render(pdf="MyTalk_v3.pdf", raw=None)
        self.assertIn("MyTalk_v3.pdf", html)
        self.assertNotIn("Raw file", html)

    def test_placeholder_when_nothing_recorded(self):
        html = self._render(pdf=None, raw=None)
        self.assertIn("Not recorded", html)


# --- #1401: re-standardize legacy filenames -------------------------------


class RestandardizeArtifactFilenamesTests(DatabaseTestCase):
    """
    Tests for the restandardize_artifact_filenames command (#1401), which
    renames legacy never-renamed files to the Author_Title_Venue scheme by
    reusing Artifact.save(). See also the #1391 capture tests above.
    """

    def _legacy_talk(self, last_name="Kim", title="My Talk", year=2019,
                     base="Original_Upload_v2"):
        """
        Build a talk with authors but NON-standard files actually present on
        disk (so the os.rename in save() has something to rename). The factory
        auto-standardizes on create, so we drop real files at non-standard
        paths and repoint the row at them, mimicking a never-renamed import.
        Returns (talk, pdf_basename, raw_basename).
        """
        person = self.make_person(last_name=last_name)
        talk = TalkFactory(title=title, forum_name="CHI",
                           date=date(year, 1, 1), authors=[person])
        pdf_name = default_storage.save(
            f"talks/{base}.pdf", ContentFile(b"%PDF-1.4 x"))
        raw_name = default_storage.save(
            f"talks/{base}.pptx", ContentFile(b"PKx"))
        Talk.objects.filter(pk=talk.pk).update(
            pdf_file=pdf_name, raw_file=raw_name,
            original_pdf_filename=os.path.basename(pdf_name),
            original_raw_filename=os.path.basename(raw_name),
        )
        talk.refresh_from_db()
        return talk, os.path.basename(pdf_name), os.path.basename(raw_name)

    def test_renames_pdf_and_raw_preserving_original_and_idempotent(self):
        talk, pdf_base, raw_base = self._legacy_talk()
        orig_pdf = talk.original_pdf_filename
        orig_raw = talk.original_raw_filename

        call_command("restandardize_artifact_filenames")

        talk.refresh_from_db()
        # Both files renamed away from the original toward the standardized
        # scheme (which contains the author last name), on disk and in the DB.
        self.assertNotIn("Original_Upload", talk.pdf_file.name)
        self.assertNotIn("Original_Upload", talk.raw_file.name)
        self.assertIn("Kim", os.path.basename(talk.pdf_file.name))
        self.assertIn("Kim", os.path.basename(talk.raw_file.name))
        self.assertTrue(default_storage.exists(talk.pdf_file.name))
        self.assertTrue(default_storage.exists(talk.raw_file.name))
        # Provenance preserved (not clobbered by the rename).
        self.assertEqual(talk.original_pdf_filename, orig_pdf)
        self.assertEqual(talk.original_raw_filename, orig_raw)

        # Idempotent: a second run leaves the now-standardized names alone.
        pdf_after = talk.pdf_file.name
        raw_after = talk.raw_file.name
        call_command("restandardize_artifact_filenames")
        talk.refresh_from_db()
        self.assertEqual(talk.pdf_file.name, pdf_after)
        self.assertEqual(talk.raw_file.name, raw_after)

    def test_already_standardized_talk_is_untouched(self):
        # A normally-created talk is auto-standardized on save, so the command
        # should find nothing to do and leave its filename unchanged.
        person = self.make_person(last_name="Lee")
        talk = TalkFactory(title="Standard Talk", forum_name="CHI",
                           date=date(2021, 1, 1), authors=[person])
        before = talk.pdf_file.name

        call_command("restandardize_artifact_filenames")

        talk.refresh_from_db()
        self.assertEqual(talk.pdf_file.name, before)

    def test_malformed_row_is_skipped_and_batch_continues(self):
        # A null-date talk can't form a standardized name; it must be skipped
        # (not renamed, no crash) while a good legacy row in the same run is
        # still re-standardized.
        bad = TalkFactory(title="Bad Row", forum_name="CHI", date=None,
                          pdf_file=_pdf("bad_upload.pdf"))
        bad_name = bad.pdf_file.name
        good, _, _ = self._legacy_talk(last_name="Park", title="Good Talk",
                                       base="Good_Original_v1")

        # Must not raise despite the malformed row.
        call_command("restandardize_artifact_filenames")

        good.refresh_from_db()
        bad.refresh_from_db()
        self.assertIn("Park", os.path.basename(good.pdf_file.name))
        self.assertNotIn("Good_Original", good.pdf_file.name)
        # The malformed row is left exactly as it was.
        self.assertEqual(bad.pdf_file.name, bad_name)
