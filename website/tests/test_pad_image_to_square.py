"""
Tests for auto-padding a non-square upload to a centered square (#1410).

The Award badge is cropped to a 1:1 square on the public Awards page (via
``image_cropping`` + Cropper.js). For a non-square logo that crops away content,
the admin instead offers a "pad to square" option that keeps the whole image and
adds blank margins. ``website.utils.fileutils.pad_image_to_square`` does that
transform server-side; ``AwardAdmin.save_model`` wires it to the checkbox.

Two styles, per the repo convention:
  * unit tests of ``pad_image_to_square`` (pure Pillow logic, no DB);
  * an integration test of ``AwardAdmin.save_model`` (the real save path).
"""

import io
import shutil
import tempfile

from PIL import Image
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings

from website.tests.base import DatabaseTestCase
from website.utils.fileutils import pad_image_to_square


def _upload(name, size, color, mode="RGB", fmt="PNG"):
    """Build a SimpleUploadedFile holding a solid-color image of ``size``."""
    img = Image.new(mode, size, color)
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return SimpleUploadedFile(name, buf.getvalue(),
                              content_type="image/" + fmt.lower())


# --- pad_image_to_square (the transform) -----------------------------------


class PadImageToSquareTests(SimpleTestCase):
    """Unit tests for the Pillow padding helper. No DB; runs in ms."""

    def _open(self, content):
        return Image.open(io.BytesIO(content.read()))

    def test_already_square_returns_none(self):
        """A square upload is left untouched so its original bytes survive."""
        result = pad_image_to_square(
            _upload("a.png", (150, 150), (10, 20, 30, 255), "RGBA", "PNG"))
        self.assertIsNone(result)

    def test_landscape_jpeg_gets_white_square(self):
        result = pad_image_to_square(
            _upload("logo.jpg", (200, 100), (0, 0, 0), "RGB", "JPEG"))
        self.assertIsNotNone(result)
        content, box = result
        self.assertEqual(box, "0,0,200,200")
        img = self._open(content)
        self.assertEqual(img.size, (200, 200))
        self.assertEqual(img.format, "JPEG")
        # Top margin is white; the centered band is the black original.
        self.assertGreater(min(img.convert("RGB").getpixel((100, 5))), 240)
        self.assertLess(max(img.convert("RGB").getpixel((100, 100))), 15)

    def test_portrait_png_gets_transparent_square(self):
        result = pad_image_to_square(
            _upload("logo.png", (100, 200), (255, 0, 0, 255), "RGBA", "PNG"))
        content, box = result
        self.assertEqual(box, "0,0,200,200")
        img = self._open(content)
        self.assertEqual(img.size, (200, 200))
        self.assertEqual(img.mode, "RGBA")
        # Left margin transparent; center is the opaque red original.
        self.assertEqual(img.getpixel((5, 100))[3], 0)
        self.assertEqual(img.getpixel((100, 100)), (255, 0, 0, 255))

    def test_webp_stays_webp_and_transparent(self):
        """WebP keeps its format with transparent margins (saved lossless so a
        lossless source isn't degraded by the padding re-encode)."""
        result = pad_image_to_square(
            _upload("logo.webp", (100, 200), (12, 34, 56, 255), "RGBA", "WEBP"))
        content, box = result
        self.assertEqual(box, "0,0,200,200")
        img = self._open(content)
        self.assertEqual(img.format, "WEBP")
        self.assertEqual(img.size, (200, 200))
        self.assertEqual(img.convert("RGBA").getpixel((5, 100))[3], 0)  # margin

    def test_content_is_centered_with_equal_margins(self):
        # 200x100 -> 200x200: content occupies rows 50..150, margins above/below.
        result = pad_image_to_square(
            _upload("c.png", (200, 100), (0, 255, 0, 255), "RGBA", "PNG"))
        content, _ = result
        img = self._open(content)
        self.assertEqual(img.getpixel((100, 25))[3], 0)    # top margin
        self.assertEqual(img.getpixel((100, 175))[3], 0)   # bottom margin
        self.assertEqual(img.getpixel((100, 100))[3], 255)  # centered content


# --- AwardAdmin.save_model wiring ------------------------------------------


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class AwardBadgePaddingAdminTests(DatabaseTestCase):
    """The checkbox path: a non-square badge is padded square on save, and a
    full-image crop box is stored so the public render doesn't crop it."""

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def _save_award(self, pad):
        from unittest.mock import MagicMock
        from website.admin.admin_site import ml_admin_site
        from website.admin.award_admin import AwardAdminForm
        from website.models import Award

        person = self.make_person()
        form = AwardAdminForm(
            data={
                "title": "Test Award",
                "date": "2024-01-01",
                "organization": "ACM",
                "award_type": "Faculty Honor",
                "recipients": [person.pk],
                "projects": [],
                "url": "",
                "description": "",
                "badge_cropping": "",
                "badge_alt_text": "",
                "pad_badge_to_square": "on" if pad else "",
            },
            files={"badge": _upload("badge.png", (200, 100),
                                    (0, 0, 255, 255), "RGBA", "PNG")},
        )
        self.assertTrue(form.is_valid(), form.errors)
        obj = form.save(commit=False)
        admin_obj = ml_admin_site._registry[Award]
        admin_obj.save_model(MagicMock(), obj, form, change=False)
        return obj

    def test_save_model_pads_badge_when_checked(self):
        obj = self._save_award(pad=True)
        with Image.open(obj.badge.path) as img:
            self.assertEqual(img.size[0], img.size[1])  # square
        self.assertEqual(obj.badge_cropping, "0,0,200,200")

    def test_save_model_leaves_badge_when_unchecked(self):
        obj = self._save_award(pad=False)
        with Image.open(obj.badge.path) as img:
            self.assertEqual(img.size, (200, 100))  # unchanged, still cropped later


# --- The add page actually renders the toggle + its assets -----------------


class AwardAddPageRendersToggleTests(DatabaseTestCase):
    """End-to-end-ish check that the change form exposes the checkbox and pulls
    in pad_to_square.js/.css, so the wiring is verified without a browser."""

    def test_add_page_has_checkbox_and_assets(self):
        from django.contrib.auth.models import User
        from django.urls import reverse

        User.objects.create_superuser("admin", "a@b.co", "pw")
        self.client.force_login(User.objects.get(username="admin"))
        resp = self.client.get(reverse("admin:website_award_add"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('name="pad_badge_to_square"', html)
        self.assertIn("pad_to_square.js", html)
        self.assertIn("pad_to_square.css", html)
