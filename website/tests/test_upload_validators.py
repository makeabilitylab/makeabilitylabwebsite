"""
Unit tests for website.utils.upload_validators (issue #6).

Pure-logic tests: each validator is a function over an uploaded file, so these
use SimpleTestCase + SimpleUploadedFile with crafted bytes — no DB, runs in ms.

Each category covers four cases:
  * accept a file whose extension AND bytes are valid,
  * reject a disallowed extension,
  * reject a renamed payload (allowed extension, wrong/dangerous bytes),
  * plus category-specific cases (HEIC guidance, .fig/.sketch for raw_file).
"""

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from website.utils.upload_validators import (
    validate_image_upload,
    validate_pdf_upload,
    validate_raw_file_upload,
    validate_video_upload,
)


# --- Sample file headers ---------------------------------------------------

PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 16
JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01" + b"\x00" * 16
GIF = b"GIF89a\x01\x00\x01\x00\x80\x00\x00" + b"\x00" * 16
WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 16
PDF = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n" + b"\x00" * 16
MP4 = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00" + b"\x00" * 16
WEBM = b"\x1aE\xdf\xa3\x01\x00\x00\x00" + b"\x00" * 16
ZIP = b"PK\x03\x04\x14\x00\x00\x00\x08\x00" + b"\x00" * 16  # pptx/docx/key/sketch/zip
OLE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 16     # legacy ppt/doc
FIG = b"fig-kiwi\x0f\x00\x00\x00\x01\x02\x03" + b"\x00" * 16  # proprietary binary
HTML = b"<!DOCTYPE html>\n<html><body>hi</body></html>"
SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'


def _upload(name, content):
    return SimpleUploadedFile(name, content)


class _CommittedFile:
    """
    Minimal stand-in for an already-stored FieldFile (``_committed = True``),
    i.e. an existing file on an unchanged record. Validators should skip it.
    """

    def __init__(self, name):
        self.name = name
        self._committed = True

    def seek(self, *a):
        raise AssertionError("a committed file should not be read by validators")

    def read(self, *a):
        raise AssertionError("a committed file should not be read by validators")


class ImageValidatorTests(SimpleTestCase):
    def test_accepts_valid_images(self):
        for name, content in [
            ("a.png", PNG), ("a.jpg", JPEG), ("a.jpeg", JPEG),
            ("a.gif", GIF), ("a.webp", WEBP),
        ]:
            with self.subTest(name=name):
                validate_image_upload(_upload(name, content))  # no raise

    def test_rejects_disallowed_extension(self):
        with self.assertRaises(ValidationError):
            validate_image_upload(_upload("a.svg", SVG))
        with self.assertRaises(ValidationError):
            validate_image_upload(_upload("a.html", HTML))

    def test_rejects_renamed_payload(self):
        # Allowed extension, but the bytes are HTML, not an image.
        with self.assertRaises(ValidationError) as ctx:
            validate_image_upload(_upload("evil.png", HTML))
        self.assertEqual(ctx.exception.code, "invalid_image_content")

    def test_heic_gets_guiding_message(self):
        for name in ("photo.heic", "photo.HEIC", "photo.heif"):
            with self.subTest(name=name):
                with self.assertRaises(ValidationError) as ctx:
                    validate_image_upload(_upload(name, PNG))
                self.assertEqual(ctx.exception.code, "heic_not_supported")


class PdfValidatorTests(SimpleTestCase):
    def test_accepts_valid_pdf(self):
        validate_pdf_upload(_upload("paper.pdf", PDF))

    def test_rejects_disallowed_extension(self):
        with self.assertRaises(ValidationError):
            validate_pdf_upload(_upload("paper.exe", PDF))

    def test_rejects_renamed_payload(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_pdf_upload(_upload("evil.pdf", HTML))
        self.assertEqual(ctx.exception.code, "invalid_pdf_content")


class VideoValidatorTests(SimpleTestCase):
    def test_accepts_valid_videos(self):
        validate_video_upload(_upload("clip.mp4", MP4))
        validate_video_upload(_upload("clip.mov", MP4))
        validate_video_upload(_upload("clip.webm", WEBM))

    def test_rejects_disallowed_extension(self):
        with self.assertRaises(ValidationError):
            validate_video_upload(_upload("clip.avi", MP4))

    def test_rejects_renamed_payload(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_video_upload(_upload("evil.mp4", HTML))
        self.assertEqual(ctx.exception.code, "invalid_video_content")


class RawFileValidatorTests(SimpleTestCase):
    def test_accepts_known_source_formats(self):
        for name, content in [
            ("talk.pptx", ZIP), ("talk.key", ZIP), ("doc.docx", ZIP),
            ("src.zip", ZIP), ("legacy.ppt", OLE), ("paper.pdf", PDF),
        ]:
            with self.subTest(name=name):
                validate_raw_file_upload(_upload(name, content))  # no raise

    def test_accepts_proprietary_design_files(self):
        # .fig / .sketch are accepted by extension; the denylist content check
        # passes any non-web-executable bytes, so we don't need their signatures.
        validate_raw_file_upload(_upload("poster.fig", FIG))
        validate_raw_file_upload(_upload("poster.sketch", ZIP))

    def test_rejects_disallowed_extension(self):
        with self.assertRaises(ValidationError):
            validate_raw_file_upload(_upload("page.html", HTML))
        with self.assertRaises(ValidationError):
            validate_raw_file_upload(_upload("image.svg", SVG))

    def test_rejects_web_executable_content_via_rename(self):
        # Allowed extension (.fig) but HTML bytes -> caught by the denylist.
        with self.assertRaises(ValidationError) as ctx:
            validate_raw_file_upload(_upload("evil.fig", HTML))
        self.assertEqual(ctx.exception.code, "invalid_raw_content")


class ExistingFileGateTests(SimpleTestCase):
    """An already-stored file (unchanged record edit) is skipped, even if its
    extension/content would fail today's rules. Re-validating it adds no
    security and would break editing legacy records."""

    def test_committed_files_are_not_validated(self):
        # Each of these would fail if validated as a new upload; the gate
        # short-circuits before the extension/content checks (and before any
        # read of the file, which _CommittedFile asserts against).
        validate_image_upload(_CommittedFile("legacy.bmp"))
        validate_pdf_upload(_CommittedFile("legacy.txt"))
        validate_video_upload(_CommittedFile("legacy.avi"))
        validate_raw_file_upload(_CommittedFile("legacy.tex"))
