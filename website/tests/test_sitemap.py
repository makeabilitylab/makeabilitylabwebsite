"""
Regression tests for the dynamic sitemap (issue #1252).

The sitemap is exercised through the real URL/view stack so a routing or
queryset regression is caught. See website/sitemaps.py.

Note: robots.txt is a static file (./robots.txt) served by Apache on the
servers, not a Django view, so it isn't covered here.
"""

import re
from datetime import date

from django.test import override_settings

from website.tests.base import DatabaseTestCase


class SitemapTests(DatabaseTestCase):
    def _make_position(self, person):
        """Give a Person a Position so it appears in the people sitemap."""
        from website.models import Position
        from website.models.position import Title
        return Position.objects.create(
            person=person, start_date=date(2020, 1, 1), title=Title.PHD_STUDENT
        )

    def test_sitemap_returns_xml(self):
        resp = self.client.get("/sitemap.xml")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("xml", resp["Content-Type"])

    def test_sitemap_includes_static_pages(self):
        body = self.client.get("/sitemap.xml").content.decode()
        # Listing pages should always be present.
        self.assertIn("/publications/", body)
        self.assertIn("/people/", body)

    def test_sitemap_includes_visible_project_excludes_private(self):
        self.make_project(name="Visible Proj", short_name="visibleproj",
                          is_visible=True)
        self.make_project(name="Private Proj", short_name="privateproj",
                          is_visible=False)
        body = self.client.get("/sitemap.xml").content.decode()
        self.assertIn("/project/visibleproj/", body)
        self.assertNotIn("/project/privateproj/", body)

    def test_sitemap_includes_person_with_position(self):
        person = self.make_person(first_name="Ada", last_name="Lovelace")
        self._make_position(person)
        body = self.client.get("/sitemap.xml").content.decode()
        self.assertIn(f"/member/{person.url_name}/", body)

    def test_sitemap_excludes_person_without_position(self):
        # No position => not on the public people page => not in the sitemap.
        person = self.make_person(first_name="Grace", last_name="Hopper")
        body = self.client.get("/sitemap.xml").content.decode()
        self.assertNotIn(f"/member/{person.url_name}/", body)

    def test_sitemap_includes_news_item(self):
        news = self.make_news_item(title="Big Lab News")
        body = self.client.get("/sitemap.xml").content.decode()
        self.assertIn(f"/news/{news.slug}/", body)

    def test_static_listing_pages_have_lastmod(self):
        # The listing pages should advertise a <lastmod> sourced from their
        # most-recent content, not be the only entries with none. Create a news
        # item so the news/home/listing sections are non-empty.
        self.make_news_item(title="Dated News")
        body = self.client.get("/sitemap.xml").content.decode()
        # Pull the <url> block for the /news/ listing and assert it carries a
        # <lastmod>. (Detail-page news URLs look like /news/<slug>/.)
        url_blocks = re.findall(r"<url>(.*?)</url>", body, re.DOTALL)
        listing = [b for b in url_blocks if re.search(r"<loc>[^<]*/news/</loc>", b)]
        self.assertTrue(listing, "expected a /news/ listing entry in the sitemap")
        self.assertIn("<lastmod>", listing[0])

    @override_settings(SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"))
    def test_sitemap_honors_forwarded_proto_header(self):
        # The sitemap scheme follows request.scheme (we no longer pin
        # protocol="https"). Behind UW CSE's TLS-terminating proxy, Django
        # reaches https via SECURE_PROXY_SSL_HEADER trusting X-Forwarded-Proto
        # (#1329). Simulate that header here and confirm every <loc> is https.
        self.make_project(name="Scheme Proj", short_name="schemeproj",
                          is_visible=True)
        body = self.client.get(
            "/sitemap.xml", HTTP_X_FORWARDED_PROTO="https"
        ).content.decode()
        locs = re.findall(r"<loc>(.*?)</loc>", body)
        self.assertTrue(locs)  # guard against an empty sitemap passing vacuously
        self.assertFalse(
            [loc for loc in locs if not loc.startswith("https://")],
            "with X-Forwarded-Proto=https the sitemap <loc> URLs should be https",
        )

    def test_sitemap_scheme_follows_request(self):
        # With the protocol pin removed, a plain request (no forwarded-proto,
        # no SECURE_PROXY_SSL_HEADER) reflects the request scheme — http here.
        # This is the local-dev / direct-request case; the proxy supplies https
        # in the deployed environments (see the test above and #1329).
        self.make_project(name="Plain Proj", short_name="plainproj",
                          is_visible=True)
        body = self.client.get("/sitemap.xml").content.decode()
        locs = re.findall(r"<loc>(.*?)</loc>", body)
        self.assertTrue(locs)
        self.assertTrue(
            all(loc.startswith("http://") for loc in locs),
            "without a forwarded-proto header the sitemap should reflect the "
            "request scheme (http) rather than a pinned https",
        )
