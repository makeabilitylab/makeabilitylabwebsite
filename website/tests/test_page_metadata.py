"""
Regression tests for per-page SEO / social-sharing metadata
(issues #1142, #1236, #1324).

These exercise the URL -> view -> template stack so a regression in the
centralized metadata block in ``base.html`` (or the ``page_meta`` a view feeds
it) is caught. They pin three things:

  * canonical + Open Graph + Twitter Card tags are present on every page type;
  * absolute URLs use ``https`` behind the proxy (the #1236 fix), driven by the
    ``site_scheme`` context processor — verified by toggling ``DEBUG``;
  * detail pages emit distinct, per-page titles/descriptions/types rather than
    the single generic site description.

See website/templates/website/base.html, website/context_processors.py, and
website/utils/metadata.py.
"""

from datetime import date

from django.test import override_settings
from django.urls import reverse

from website.tests.base import DatabaseTestCase


def _position(person, title=None):
    """Give a Person a Position so its member page is fully populated."""
    from website.models import Position
    from website.models.position import Title
    return Position.objects.create(
        person=person, start_date=date(2020, 1, 1),
        title=title or Title.PHD_STUDENT,
    )


# On the servers DEBUG is False, so site_scheme pins https — assert against that
# (the test client's host is "testserver", auto-added to ALLOWED_HOSTS).
@override_settings(DEBUG=False)
class PageMetadataHttpsTests(DatabaseTestCase):

    def test_home_has_core_metadata(self):
        resp = self.client.get(reverse("website:index"))
        self.assertEqual(resp.status_code, 200)
        # Canonical present and https.
        self.assertContains(resp, '<link rel="canonical" href="https://testserver/">')
        # Open Graph essentials.
        self.assertContains(resp, '<meta property="og:site_name" content="Makeability Lab">')
        self.assertContains(resp, '<meta property="og:type" content="website">')
        self.assertContains(resp, '<meta property="og:url" content="https://testserver/">')
        # Twitter Card.
        self.assertContains(resp, '<meta name="twitter:card" content="summary_large_image">')

    def test_no_http_scheme_in_social_urls(self):
        """#1236: og:url / og:image / canonical must never advertise http://."""
        resp = self.client.get(reverse("website:index"))
        self.assertNotContains(resp, 'property="og:url" content="http://')
        self.assertNotContains(resp, 'property="og:image" content="http://')
        self.assertNotContains(resp, 'rel="canonical" href="http://')

    def test_project_detail_metadata(self):
        project = self.make_project(
            name="Sound Watch", short_name="soundwatch", is_visible=True,
            start_date=date(2020, 1, 1),
            summary="SoundWatch is a smartwatch system for sound awareness.",
        )
        resp = self.client.get(reverse("website:project", args=[project.short_name]))
        self.assertEqual(resp.status_code, 200)
        # Canonical matches the sitemap's reverse()-built URL exactly.
        canonical = "https://testserver" + reverse("website:project", args=[project.short_name])
        self.assertContains(resp, f'<link rel="canonical" href="{canonical}">')
        self.assertContains(resp, f'<meta property="og:url" content="{canonical}">')
        self.assertContains(resp, '<meta property="og:title" content="Sound Watch">')
        self.assertContains(resp, '<meta property="og:type" content="website">')
        # Per-page description derived from the project summary (not the default).
        self.assertContains(resp, "smartwatch system for sound awareness")

    def test_member_detail_metadata(self):
        person = self.make_person(first_name="Ada", last_name="Lovelace",
                                  bio="Ada researches accessible computing.")
        _position(person)
        resp = self.client.get(
            reverse("website:member_by_name", kwargs={"member_name": person.url_name})
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '<meta property="og:type" content="profile">')
        self.assertContains(resp, '<meta property="og:title" content="Ada Lovelace - Makeability Lab">')
        self.assertContains(resp, '<meta property="og:profile:first_name" content="Ada">')
        self.assertContains(resp, '<meta property="og:profile:last_name" content="Lovelace">')
        canonical = "https://testserver" + reverse(
            "website:member_by_name", kwargs={"member_name": person.url_name})
        self.assertContains(resp, f'<link rel="canonical" href="{canonical}">')
        # Description comes from the bio, not the generic site default.
        self.assertContains(resp, "Ada researches accessible computing")

    def test_news_detail_metadata(self):
        item = self.make_news_item(
            title="Lab wins best paper",
            content="The Makeability Lab won a best paper award at CHI.",
        )
        resp = self.client.get(
            reverse("website:news_item_by_id", kwargs={"id": item.id})
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '<meta property="og:type" content="article">')
        self.assertContains(resp, '<meta property="og:title" content="Lab wins best paper">')
        self.assertContains(resp, '<meta property="og:article:published_time"')
        self.assertContains(resp, '<link rel="canonical" href="https://testserver/news/')
        self.assertContains(resp, "won a best paper award")


class ListPageDescriptionTests(DatabaseTestCase):
    """Each listing page should ship a distinct, hand-written meta description
    and og:title rather than the single generic site description (#1142/#1324)."""

    GENERIC = "advanced research lab in Human-Computer Interaction and AI"

    def _assert_distinct(self, url_name, og_title, description_fragment):
        resp = self.client.get(reverse(url_name))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, f'<meta property="og:title" content="{og_title}">')
        self.assertContains(resp, description_fragment)
        # The per-page description should appear in the description meta tag.
        self.assertContains(resp, f'<meta name="description" content="{description_fragment}')

    def test_people_description(self):
        self._assert_distinct("website:people", "People",
                              "Meet the faculty, students, postdocs, and alumni")

    def test_projects_description(self):
        self._assert_distinct("website:projects", "Projects",
                              "Explore Makeability Lab research projects")

    def test_publications_description(self):
        self._assert_distinct("website:publications", "Publications",
                              "Peer-reviewed Makeability Lab publications")

    def test_awards_description(self):
        self._assert_distinct("website:awards", "Awards",
                              "Awards and honors earned by Makeability Lab members")

    def test_news_description(self):
        self._assert_distinct("website:news_listing", "News",
                              "News from the Makeability Lab")

    def test_descriptions_are_not_the_generic_default(self):
        for url_name in ("website:people", "website:projects",
                         "website:publications", "website:awards",
                         "website:news_listing"):
            resp = self.client.get(reverse(url_name))
            self.assertNotContains(resp, f'name="description" content="The Makeability Lab is an {self.GENERIC}')


class PageMetadataSchemeTests(DatabaseTestCase):

    @override_settings(DEBUG=True)
    def test_local_dev_uses_request_scheme(self):
        """In DEBUG (local dev over http) the absolute URLs follow request.scheme."""
        resp = self.client.get(reverse("website:index"))
        self.assertContains(resp, '<link rel="canonical" href="http://testserver/">')
        self.assertContains(resp, '<meta property="og:url" content="http://testserver/">')
