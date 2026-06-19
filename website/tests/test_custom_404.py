"""
Regression tests for the custom 404 page (#1190).

A custom ``handler404`` only takes effect when ``DEBUG=False`` -- which is the
default under the test settings -- so the Django test client exercises the real
error path here without any DEBUG hackery (the local-dev preview route, which is
the part that needs DEBUG=True, is covered separately below by asserting it stays
*off* in production-like settings).

These run as ``DatabaseTestCase`` because the page extends ``base.html``, whose
footer touches the request/template stack; using the DB-backed base keeps it
consistent with the rest of the view-layer suite.
"""

from django.urls import NoReverseMatch, reverse

from website.tests.base import DatabaseTestCase


class Custom404Tests(DatabaseTestCase):
    """The handler404 wiring renders our branded template with a 404 status."""

    # A path that matches no URL pattern (the catch-all project route is
    # commented out in website/urls.py, so a single bogus segment 404s).
    BOGUS_URL = "/this-page-does-not-exist-1190/"

    def test_unknown_url_returns_404_status(self):
        response = self.client.get(self.BOGUS_URL)
        self.assertEqual(response.status_code, 404)

    def test_unknown_url_uses_custom_template(self):
        response = self.client.get(self.BOGUS_URL)
        self.assertTemplateUsed(response, "website/404.html")

    def test_404_page_offers_a_way_home(self):
        """The page must surface real navigation, not just the animation."""
        response = self.client.get(self.BOGUS_URL)
        html = response.content.decode()
        # The recovery links are the whole point: a lost visitor needs routes
        # out. Assert the key destinations are present and linked.
        self.assertIn(reverse("website:index"), html)
        self.assertIn(reverse("website:people"), html)
        self.assertIn(reverse("website:publications"), html)
        self.assertIn(reverse("website:projects"), html)

    def test_404_page_does_not_leak_raw_requested_path(self):
        """
        The requested path is echoed back, but must be HTML-escaped so a crafted
        URL can't inject markup (reflected-XSS guard). Django autoescaping does
        this; this test pins it so a future {% autoescape off %} can't regress it.
        """
        response = self.client.get("/<script>alert(1)</script>/")
        self.assertEqual(response.status_code, 404)
        self.assertNotIn("<script>alert(1)</script>", response.content.decode())


class Custom404PreviewRouteTests(DatabaseTestCase):
    """The dev-only preview route must never exist in production-like settings."""

    def test_preview_route_absent_when_not_debug(self):
        # Under the test settings DEBUG is False, mirroring production. The
        # preview route is registered only `if settings.DEBUG`, so it should
        # neither reverse nor resolve here.
        with self.assertRaises(NoReverseMatch):
            reverse("website:custom_404_preview")
        self.assertEqual(self.client.get("/404-preview/").status_code, 404)
