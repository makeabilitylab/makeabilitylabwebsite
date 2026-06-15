"""Tests for Artifact model methods (filename-drift check, raw-file label)."""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase


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
