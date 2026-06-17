"""
Upload file-type validation for user-supplied media (issue #6).

All uploads enter through the Django admin (staff/superuser only), so this is
defense-in-depth: it stops a careless or compromised account from placing a
browser-executable file (e.g. ``.svg`` / ``.html``) on a public ``/media/``
path, where the web server would serve it as active content (stored XSS). It
also rejects plainly wrong file types (e.g. a ``.pages`` headshot) before they
break the thumbnail pipeline.

Two layers, no third-party dependency:

1. **Extension allowlist** via Django's ``FileExtensionValidator``.
2. **Magic-byte content sniff** so a renamed payload (``evil.html`` saved as
   ``evil.pdf``) is still caught.

The content strategy differs by field, on purpose:

* **images / PDFs / videos** use a *positive* check — the bytes must match a
  known-good signature. These formats are few, stable, and well known.
* **raw_file** (talk/poster/pub source files) uses a *negative* check. It
  accepts a broad, growing set of proprietary source formats (pptx, key, fig,
  sketch, zip, ...) whose byte signatures we can't practically enumerate or
  keep current, and only *rejects* bytes that look like browser-executable web
  content. The security goal for raw_file was always "don't let it be served
  as active web content," which a denylist expresses more honestly than a
  positive allowlist (which would force us to chase a magic number for every
  new design tool).

Validators run during ``full_clean()``, which the admin's ModelForms call, so
they enforce exactly at the upload surface. They intentionally do *not* run on
a bare ``.save()`` (management commands, signals); that path is not the threat
model.

These are plain module-level functions so Django serializes them into the
(per-environment, regenerated) migrations by dotted path, with no equality or
deconstruction surprises.

Usage::

    from website.utils.upload_validators import validate_image_upload
    image = models.ImageField(..., validators=[validate_image_upload])
"""

import os

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.core.validators import FileExtensionValidator

# --- Extension allowlists --------------------------------------------------

IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "gif", "webp"]
PDF_EXTENSIONS = ["pdf"]
VIDEO_EXTENSIONS = ["mp4", "webm", "mov", "m4v"]
# raw_file is a grab-bag of source formats. pptx/docx/key/sketch are all ZIP
# containers underneath; ppt/doc are legacy OLE; fig is a proprietary Figma
# binary. We can't positively fingerprint them all, so the content check below
# is a denylist (see module docstring).
RAW_FILE_EXTENSIONS = [
    "pdf", "ppt", "pptx", "key", "doc", "docx", "zip", "fig", "sketch",
]


# --- New-upload gate -------------------------------------------------------


def _is_new_upload(value):
    """
    True only for a freshly uploaded file (not an already-stored one).

    Django re-runs field validators on every ``full_clean()``, including when an
    admin saves an existing record without touching its file. We skip those:
    a committed file is already stored and served, so re-validating it adds no
    security, and enforcing today's rules on a legacy file (e.g. a ``raw_file``
    uploaded before these rules existed) would wrongly block the edit.

    A new upload assigned to a FileField is wrapped as a ``FieldFile`` with
    ``_committed == False``; an unchanged stored file has ``_committed == True``.
    Direct calls in tests pass an ``UploadedFile``.
    """
    if isinstance(value, UploadedFile):
        return True
    return not getattr(value, "_committed", True)


# --- Header sniffing -------------------------------------------------------


def _read_header(value, num_bytes=1024):
    """
    Return the first ``num_bytes`` of an uploaded file as bytes.

    Seeks back to 0 afterward so the subsequent storage save (which reads from
    the current position) writes the whole file. Returns ``b""`` if the file
    can't be read, in which case the caller's content check is skipped and only
    the extension allowlist applies.
    """
    try:
        value.seek(0)
        header = value.read(num_bytes) or b""
        value.seek(0)
    except (OSError, ValueError, AttributeError):
        return b""
    return header if isinstance(header, bytes) else bytes(header)


def _looks_like_image(header):
    """True if the header matches a PNG, JPEG, GIF, or WebP signature."""
    return (
        header.startswith(b"\x89PNG\r\n\x1a\n")            # PNG
        or header.startswith(b"\xff\xd8\xff")              # JPEG
        or header.startswith(b"GIF87a")                    # GIF
        or header.startswith(b"GIF89a")                    # GIF
        or (header[:4] == b"RIFF" and header[8:12] == b"WEBP")  # WebP
    )


def _looks_like_pdf(header):
    """True if the header contains the PDF signature (allowing a small BOM/WS offset)."""
    return b"%PDF-" in header[:1024]


def _looks_like_video(header):
    """True if the header matches an ISO-BMFF (mp4/mov/m4v) or Matroska/WebM signature."""
    return (
        header[4:8] == b"ftyp"                  # ISO base media: mp4, mov, m4v
        or header.startswith(b"\x1aE\xdf\xa3")  # EBML: webm / matroska
    )


def _looks_like_web_executable(header):
    """
    True if the header looks like browser-executable web content
    (HTML / SVG / XML), which must never be served from a public media path.
    """
    stripped = header.lstrip().lower()
    return (
        stripped.startswith(b"<!doctype")
        or stripped.startswith(b"<html")
        or stripped.startswith(b"<svg")
        or stripped.startswith(b"<?xml")     # XHTML, SVG-in-XML
        or stripped.startswith(b"<script")
    )


def _extension(value):
    """Lower-cased extension (no dot) of the uploaded file's name."""
    return os.path.splitext(value.name)[1].lower().lstrip(".")


# --- Validators ------------------------------------------------------------


def validate_image_upload(value):
    """
    Validate an uploaded image: allowlisted raster extension + matching bytes.

    HEIC/HEIF is rejected with a guiding message: most browsers can't render it
    and Pillow/easy_thumbnails can't process it without ``pillow-heif``, so it
    would produce broken images. (HEIC->JPEG conversion on upload is tracked
    separately.)
    """
    if not _is_new_upload(value):
        return
    if _extension(value) in ("heic", "heif"):
        raise ValidationError(
            "HEIC/HEIF images aren't supported by most web browsers. Please "
            "convert the image to JPEG or PNG before uploading.",
            code="heic_not_supported",
        )
    FileExtensionValidator(allowed_extensions=IMAGE_EXTENSIONS)(value)
    header = _read_header(value)
    if header and not _looks_like_image(header):
        raise ValidationError(
            "This file doesn't look like a valid image (expected PNG, JPEG, "
            "GIF, or WebP). The file extension may not match its contents.",
            code="invalid_image_content",
        )


def validate_pdf_upload(value):
    """Validate an uploaded PDF: ``.pdf`` extension + ``%PDF-`` signature."""
    if not _is_new_upload(value):
        return
    FileExtensionValidator(allowed_extensions=PDF_EXTENSIONS)(value)
    header = _read_header(value)
    if header and not _looks_like_pdf(header):
        raise ValidationError(
            "This file doesn't look like a valid PDF. The file extension may "
            "not match its contents.",
            code="invalid_pdf_content",
        )


def validate_video_upload(value):
    """Validate an uploaded video: allowlisted extension + MP4/WebM/MOV signature."""
    if not _is_new_upload(value):
        return
    FileExtensionValidator(allowed_extensions=VIDEO_EXTENSIONS)(value)
    header = _read_header(value)
    if header and not _looks_like_video(header):
        raise ValidationError(
            "This file doesn't look like a valid video (expected MP4, WebM, or "
            "MOV). The file extension may not match its contents.",
            code="invalid_video_content",
        )


def validate_raw_file_upload(value):
    """
    Validate a raw source file: allowlisted extension + a denylist content
    check that rejects browser-executable (HTML/SVG/XML) content.

    Unlike the image/pdf/video validators, this accepts any file whose bytes
    are *not* web-executable, because raw_file holds a broad set of proprietary
    source formats (pptx, key, fig, sketch, ...) we can't positively fingerprint.
    """
    if not _is_new_upload(value):
        return
    FileExtensionValidator(allowed_extensions=RAW_FILE_EXTENSIONS)(value)
    header = _read_header(value)
    if _looks_like_web_executable(header):
        raise ValidationError(
            "This file appears to contain web/HTML content, which isn't allowed "
            "as a raw source file.",
            code="invalid_raw_content",
        )
