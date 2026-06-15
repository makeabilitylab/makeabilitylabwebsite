"""
Regression tests for the dynamic sitemap and robots.txt (issue #1252).

Both endpoints are exercised through the real URL/view stack so a routing or
queryset regression is caught. See website/sitemaps.py and
website/views/robots.py.
"""

import os
from datetime import date
from unittest import mock

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


class RobotsTxtTests(DatabaseTestCase):
    def test_robots_is_plain_text(self):
        resp = self.client.get("/robots.txt")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "text/plain")

    @mock.patch.dict(os.environ, {"DJANGO_ENV": "PROD"})
    def test_robots_prod_allows_and_advertises_sitemap(self):
        body = self.client.get("/robots.txt").content.decode()
        self.assertIn("Allow: /", body)
        self.assertIn("Sitemap:", body)
        self.assertIn("/sitemap.xml", body)

    @mock.patch.dict(os.environ, {"DJANGO_ENV": "TEST"})
    def test_robots_non_prod_disallows_all(self):
        body = self.client.get("/robots.txt").content.decode()
        self.assertIn("Disallow: /", body)
        self.assertNotIn("Allow: /", body)
