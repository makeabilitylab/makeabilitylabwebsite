"""Regression tests for serving publication thumbnail images (issue #1173).

Production Apache proxies *all* of ``/media/publications/`` to Django so the
``serve_pdf`` view can fuzzy-match renamed PDF links. That proxy scope also
captures ``/media/publications/images/*`` (the easy-thumbnails output). In
production ``DEBUG=False``, Django otherwise serves no media at all —
``static()`` returns ``[]`` and the debug-only media route in
``makeabilitylab/urls.py`` is disabled — so every publication thumbnail 404'd
*even though the files were present on disk*.

``website/urls.py`` adds an unconditional route mapping
``/media/publications/images/<path>`` to ``django.views.static.serve``. These
tests pin that the route (a) resolves ahead of / instead of ``serve_pdf``, and
(b) actually serves a file when ``DEBUG=False`` (the condition that broke prod).
"""

import os

from django.test import SimpleTestCase, override_settings
from django.urls import resolve
from django.views.static import serve


class ServePublicationImageRoutingTests(SimpleTestCase):
    def test_image_url_resolves_to_static_serve(self):
        """A /media/publications/images/ URL maps to the static serve view,
        not serve_pdf and not a 404."""
        match = resolve(
            "/media/publications/images/Foo_CHI2026.jpg.300x0_q85_detail.jpg"
        )
        self.assertEqual(match.url_name, "serve_publication_image")
        self.assertIs(match.func, serve)

    def test_image_route_document_root_is_publications_images(self):
        """The route serves out of MEDIA_ROOT/publications/images so the
        captured <path> is just the bare filename."""
        match = resolve("/media/publications/images/Foo_CHI2026.jpg")
        self.assertTrue(
            match.kwargs["document_root"].endswith(
                os.path.join("publications", "images")
            )
        )

    def test_pdf_url_still_resolves_to_serve_pdf(self):
        """The more-specific image route must not steal single-segment PDF
        requests away from serve_pdf (which does fuzzy matching)."""
        match = resolve("/media/publications/Foo_CHI2026.pdf")
        self.assertEqual(match.url_name, "serve_pdf")


class ServePublicationImageServingTests(SimpleTestCase):
    """End-to-end: the thumbnail is actually served with DEBUG=False.

    Writes a throwaway file into the route's bound document_root (read back
    from the resolved match so we hit the real path the URLconf uses), then
    removes it. This reproduces the exact prod condition: DEBUG off, file on
    disk, request proxied to Django.
    """

    def test_thumbnail_served_with_debug_false(self):
        filename = "__issue1173_regression_probe.jpg.300x0_q85_detail.jpg"
        match = resolve(f"/media/publications/images/{filename}")
        document_root = match.kwargs["document_root"]
        os.makedirs(document_root, exist_ok=True)
        file_path = os.path.join(document_root, filename)
        with open(file_path, "wb") as f:
            f.write(b"\xff\xd8\xff\xe0 fake-jpeg-bytes")
        try:
            with override_settings(DEBUG=False):
                response = self.client.get(
                    f"/media/publications/images/{filename}"
                )
            self.assertEqual(response.status_code, 200)
        finally:
            os.remove(file_path)
