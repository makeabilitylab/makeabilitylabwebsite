"""
Regression tests for the hero carousel motion accessibility work (#1294).

These pin the *template contract* the reduced-motion JS depends on, rendered
through the real index view / base template:

1. The hero ``<video>`` keeps its ``autoplay`` attribute. This is deliberate
   (progressive enhancement): with JS disabled the video must still play exactly
   as before; carousel.js pauses it under ``prefers-reduced-motion`` and via the
   pause control. A regression that drops ``autoplay`` would silently break the
   no-JS baseline — so we lock it here.
2. A ``poster`` is emitted for the video when the banner has an image, so a
   still frame shows while the video is paused.
3. The WCAG 2.2.2 pause/play control (``.carousel-motion-toggle``) is present.

The JS behavior itself (pausing under reduced motion, toggling) is verified
manually + via Pa11y; these tests guard the markup it hooks into.
"""

import tempfile

from django.test import override_settings
from django.urls import reverse

from website.models import Banner
from website.tests.base import DatabaseTestCase


def _make_png_upload(name="poster.png", size=(1600, 500)):
    """A real (tiny) in-memory PNG so easy_thumbnails can generate a poster."""
    from io import BytesIO

    from PIL import Image
    from django.core.files.uploadedfile import SimpleUploadedFile

    buffer = BytesIO()
    Image.new("RGB", size, (90, 9, 121)).save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


class HeroVideoMarkupTests(DatabaseTestCase):
    """The hero <video> markup contract that the #1294 JS relies on."""

    def _get_index(self):
        return self.client.get(reverse("website:index"))

    def test_video_banner_keeps_autoplay(self):
        """autoplay must stay in the markup (no-JS baseline must still play)."""
        Banner.objects.create(
            title="Vid", landing_page=True, video="banner/videos/clip.mp4"
        )
        html = self._get_index().content.decode()
        self.assertIn("<video", html)
        self.assertIn("autoplay", html)

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_video_banner_with_image_emits_poster(self):
        """A banner image becomes the video's poster (still frame when paused)."""
        Banner.objects.create(
            title="VidWithPoster",
            landing_page=True,
            video="banner/videos/clip.mp4",
            image=_make_png_upload(),
        )
        html = self._get_index().content.decode()
        self.assertIn("<video", html)
        self.assertIn("poster=", html)

    def test_video_banner_without_image_has_no_poster(self):
        """No banner image -> no poster attribute (browser uses first frame)."""
        Banner.objects.create(
            title="VidNoPoster", landing_page=True, video="banner/videos/clip.mp4"
        )
        html = self._get_index().content.decode()
        self.assertIn("<video", html)
        self.assertNotIn("poster=", html)


class CarouselPauseControlTests(DatabaseTestCase):
    """WCAG 2.2.2 pause/play control is present in the carousel markup."""

    def test_pause_control_rendered(self):
        Banner.objects.create(
            title="Vid", landing_page=True, video="banner/videos/clip.mp4"
        )
        html = self.client.get(reverse("website:index")).content.decode()
        self.assertIn("carousel-motion-toggle", html)
