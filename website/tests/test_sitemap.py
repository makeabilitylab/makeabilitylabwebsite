"""
Regression tests for the dynamic sitemap (issue #1252).

The sitemap is exercised through the real URL/view stack so a routing or
queryset regression is caught. See website/sitemaps.py.

Note: robots.txt is a static file (./robots.txt) served by Apache on the
servers, not a Django view, so it isn't covered here.
"""

import re
from datetime import date

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

    def test_sitemap_uses_https_scheme(self):
        # Apache proxies to Django over plain HTTP, so without a pinned
        # protocol the <loc> URLs would be http:// and only 302-redirect to
        # https. Every <loc> must be canonical https. See _HttpsSitemap.
        self.make_project(name="Scheme Proj", short_name="schemeproj",
                          is_visible=True)
        body = self.client.get("/sitemap.xml").content.decode()
        locs = re.findall(r"<loc>(.*?)</loc>", body)
        self.assertTrue(locs)  # guard against an empty sitemap passing vacuously
        self.assertFalse(
            [loc for loc in locs if not loc.startswith("https://")],
            "all sitemap <loc> URLs should use the https scheme",
        )
