"""Unit tests for the pure filename helpers in website.utils.fileutils (#1278, item 5).

These build the deterministic, archive-friendly filenames the artifact rename
pipeline depends on (get_filename_for_artifact and friends). The Star Wars
image helpers in this module are already covered by test_easter_egg_picker;
the filesystem-touching helpers (thumbnail generation, PDF page count) are left
to integration coverage. No DB.
"""

import os
import tempfile
from datetime import date

from django.test import SimpleTestCase

from website.utils.fileutils import (
    ensure_filename_is_unique,
    get_ckeditor_image_filename,
    get_filename_for_artifact,
    get_filename_no_ext,
    get_filename_without_ext_for_artifact,
    is_image,
    rename_artifact_on_filesystem,
)


class _FakeFileField:
    """Minimal stand-in for a Django FieldFile: just the .path/.name the
    on-filesystem rename helper reads and writes (no DB, no storage)."""

    def __init__(self, path):
        self.path = path
        self.name = os.path.basename(path)


class RenameArtifactExtensionTests(SimpleTestCase):
    """rename_artifact_on_filesystem must preserve the file extension even when
    the standardized base name contains dots (#1390). The old splitext()-based
    check mistook the text after the last dot for an extension and renamed the
    file extension-less on disk, which then broke thumbnail generation."""

    def _rename(self, old_basename, new_base):
        with tempfile.TemporaryDirectory() as d:
            old_path = os.path.join(d, old_basename)
            with open(old_path, "wb") as fh:
                fh.write(b"%PDF-1.4 test")
            field = _FakeFileField(old_path)
            rename_artifact_on_filesystem(field, new_base)
            return field.name  # basename of the renamed file

    def test_dotted_base_keeps_pdf_extension(self):
        # "D.C." would make splitext see ".C.ArtScience...2014" as the extension.
        new_name = self._rename(
            "Old_zVYlRJ8.pdf",
            "Froehlich_SocialFabrics_NationalAcademyofSciencesD.C.ArtScience2014",
        )
        self.assertTrue(new_name.endswith(".pdf"), new_name)

    def test_dotless_base_still_gets_extension(self):
        new_name = self._rename("Old.pdf", "Froehlich_AStandardTalk_CHI2024")
        self.assertTrue(new_name.endswith(".pdf"), new_name)

    def test_extension_not_doubled_when_already_present(self):
        new_name = self._rename("Old.pdf", "Froehlich_AStandardTalk_CHI2024.pdf")
        self.assertTrue(new_name.endswith(".pdf"), new_name)
        self.assertFalse(new_name.endswith(".pdf.pdf"), new_name)


class IsImageTests(SimpleTestCase):
    def test_known_image_extensions(self):
        for name in ("photo.jpg", "PHOTO.JPEG", "art.png", "anim.gif"):
            self.assertTrue(is_image(name), name)

    def test_non_image_extensions(self):
        for name in ("doc.pdf", "deck.pptx", "noext"):
            self.assertFalse(is_image(name), name)


class GetCkeditorImageFilenameTests(SimpleTestCase):
    def test_uppercases_filename(self):
        self.assertEqual(get_ckeditor_image_filename("My File.png"), "MY FILE.PNG")


class GetFilenameNoExtTests(SimpleTestCase):
    def test_strips_path_and_extension(self):
        self.assertEqual(
            get_filename_no_ext("publications/Doe_Paper_CHI2022.pdf"),
            "Doe_Paper_CHI2022",
        )


class GetFilenameForArtifactTests(SimpleTestCase):
    """The canonical Lastname_Title_Forum+Year naming used for archived files."""

    def test_basic_filename(self):
        self.assertEqual(
            get_filename_for_artifact(
                "Froehlich", "This Is A Test", "CHI", date(2022, 1, 1), "pdf"
            ),
            "Froehlich_ThisIsATest_CHI2022.pdf",
        )

    def test_extension_normalized_with_or_without_dot(self):
        with_dot = get_filename_for_artifact(
            "Doe", "Paper", "UIST", date(2021, 1, 1), ".pdf"
        )
        without_dot = get_filename_for_artifact(
            "Doe", "Paper", "UIST", date(2021, 1, 1), "pdf"
        )
        self.assertEqual(with_dot, without_dot)
        self.assertTrue(with_dot.endswith(".pdf"))

    def test_missing_last_name_uses_none_placeholder(self):
        self.assertTrue(
            get_filename_without_ext_for_artifact(
                "", "Paper", "CHI", date(2022, 1, 1)
            ).startswith("None_")
        )

    def test_suffix_is_inserted_before_forum(self):
        self.assertEqual(
            get_filename_without_ext_for_artifact(
                "Doe", "Paper", "CHI", date(2022, 1, 1), suffix="poster"
            ),
            "Doe_Paper_poster_CHI2022",
        )

    def test_title_truncation(self):
        result = get_filename_without_ext_for_artifact(
            "Doe", "A Very Long Title Here", "CHI", date(2022, 1, 1),
            max_pub_title_length=5,
        )
        # Title portion (between the underscores) is capped at 5 chars.
        title_part = result.split("_")[1]
        self.assertEqual(len(title_part), 5)


class EnsureFilenameIsUniqueTests(SimpleTestCase):
    def test_nonexistent_path_returned_unchanged(self):
        path = os.path.join("/tmp", "definitely-not-a-real-file-1278.pdf")
        self.assertEqual(ensure_filename_is_unique(path), path)
