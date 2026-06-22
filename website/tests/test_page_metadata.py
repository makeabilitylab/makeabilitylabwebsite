"""
Regression tests for per-page SEO / social-sharing metadata
(issues #1142, #1236, #1324).

These exercise the URL -> view -> template stack so a regression in the
centralized metadata block in ``base.html`` (or the ``page_meta`` a view feeds
it) is caught. They pin three things:

  * canonical + Open Graph + Twitter Card tags are present on every page type;
  * absolute URLs follow ``request.scheme`` — https behind the proxy because
    ``SECURE_PROXY_SSL_HEADER`` trusts the proxy's ``X-Forwarded-Proto`` header
    (#1329, which replaced the #1236 ``site_scheme`` workaround);
  * detail pages emit distinct, per-page titles/descriptions/types rather than
    the single generic site description.

See website/templates/website/base.html and website/utils/metadata.py.
"""

import json
import re
from datetime import date

from django.test import override_settings
from django.urls import reverse

from website.tests.base import DatabaseTestCase


def _extract_jsonld(test, resp):
    """Pull the JSON-LD block out of a response and parse it (fails the test if
    it's missing or not valid JSON)."""
    test.assertEqual(resp.status_code, 200)
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>',
                  resp.content.decode(), re.DOTALL)
    test.assertIsNotNone(m, "expected a JSON-LD <script> block")
    return json.loads(m.group(1)), m.group(1)


def _position(person, title=None):
    """Give a Person a Position so its member page is fully populated."""
    from website.models import Position
    from website.models.position import Title
    return Position.objects.create(
        person=person, start_date=date(2020, 1, 1),
        title=title or Title.PHD_STUDENT,
    )


# Absolute URLs follow request.scheme. We issue secure (https) requests to mirror
# the deployed servers, where SECURE_PROXY_SSL_HEADER makes request.scheme https
# behind the TLS proxy (see PageMetadataSchemeTests for the header-driven path).
# The test client's host is "testserver", auto-added to ALLOWED_HOSTS.
class PageMetadataHttpsTests(DatabaseTestCase):
    # Requests are issued with secure=True so request.scheme == "https", mirroring
    # the deployed servers where SECURE_PROXY_SSL_HEADER makes the scheme https
    # behind the TLS proxy.

    def test_home_has_core_metadata(self):
        resp = self.client.get(reverse("website:index"), secure=True)
        self.assertEqual(resp.status_code, 200)
        # Canonical present and https.
        self.assertContains(resp, '<link rel="canonical" href="https://testserver/">')
        # Open Graph essentials.
        self.assertContains(resp, '<meta property="og:site_name" content="Makeability Lab">')
        self.assertContains(resp, '<meta property="og:type" content="website">')
        self.assertContains(resp, '<meta property="og:url" content="https://testserver/">')
        # Twitter Card.
        self.assertContains(resp, '<meta name="twitter:card" content="summary_large_image">')

    def test_home_title_is_not_duplicated(self):
        """The home <title> must not be "Makeability Lab | Makeability Lab".

        base.html appends " | Makeability Lab", so the index pagetitle block
        must carry only a descriptive prefix, not the lab name again.
        """
        resp = self.client.get(reverse("website:index"), secure=True)
        self.assertNotContains(resp, "<title>Makeability Lab | Makeability Lab</title>")
        self.assertContains(
            resp, "<title>HCI &amp; AI Research at UW | Makeability Lab</title>"
        )

    def test_no_http_scheme_in_social_urls(self):
        """#1236: og:url / og:image / canonical must never advertise http://."""
        resp = self.client.get(reverse("website:index"), secure=True)
        self.assertNotContains(resp, 'property="og:url" content="http://')
        self.assertNotContains(resp, 'property="og:image" content="http://')
        self.assertNotContains(resp, 'rel="canonical" href="http://')

    def test_project_detail_metadata(self):
        project = self.make_project(
            name="Sound Watch", short_name="soundwatch", is_visible=True,
            start_date=date(2020, 1, 1),
            summary="SoundWatch is a smartwatch system for sound awareness.",
        )
        resp = self.client.get(reverse("website:project", args=[project.short_name]), secure=True)
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
            reverse("website:member_by_name", kwargs={"member_name": person.url_name}),
            secure=True,
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
            reverse("website:news_item_by_id", kwargs={"id": item.id}),
            secure=True,
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
                              "Meet the faculty, students, and alumni")

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


class JsonLdTests(DatabaseTestCase):
    """schema.org JSON-LD structured data (#1324). Every block must be present
    and parse as valid JSON (guards against template-escaping bugs)."""

    def test_home_emits_organization(self):
        data, _ = _extract_jsonld(self, self.client.get(reverse("website:index")))
        self.assertEqual(data["@type"], "Organization")
        self.assertEqual(data["name"], "Makeability Lab")
        self.assertIn("sameAs", data)

    def test_member_emits_person_with_sameas(self):
        person = self.make_person(
            first_name="Ada", last_name="Lovelace",
            orcid="https://orcid.org/0000-0002-1853-9710",
        )
        _position(person)
        data, _ = _extract_jsonld(self, self.client.get(
            reverse("website:member_by_name", kwargs={"member_name": person.url_name})))
        self.assertEqual(data["@type"], "Person")
        self.assertEqual(data["name"], "Ada Lovelace")
        self.assertIn("https://orcid.org/0000-0002-1853-9710", data["sameAs"])

    def test_news_emits_newsarticle(self):
        item = self.make_news_item(title="Lab wins award", content="Body text.")
        data, _ = _extract_jsonld(self, self.client.get(
            reverse("website:news_item_by_id", kwargs={"id": item.id})))
        self.assertEqual(data["@type"], "NewsArticle")
        self.assertEqual(data["headline"], "Lab wins award")
        self.assertIn("datePublished", data)

    def test_jsonld_escapes_script_breakout(self):
        """A title containing </script> must not break out of the ld+json tag."""
        item = self.make_news_item(title="Pwn </script><b>x</b>", content="x")
        data, block = _extract_jsonld(self, self.client.get(
            reverse("website:news_item_by_id", kwargs={"id": item.id})))
        self.assertNotIn("</script>", block)       # escaped, not literal
        self.assertIn("\\u003c", block)
        self.assertEqual(data["headline"], "Pwn </script><b>x</b>")  # round-trips


class DescriptionFallbackTests(DatabaseTestCase):
    """Distinct, length-bounded descriptions instead of the generic boilerplate
    (#1142/#1324): home mirrors the hero blurb; summary-less projects use About."""

    def _meta_description(self, resp):
        m = re.search(r'name="description" content="([^"]*)"', resp.content.decode())
        return m.group(1) if m else None

    def test_home_uses_distinct_hero_description(self):
        resp = self.client.get(reverse("website:index"))
        desc = self._meta_description(resp)
        self.assertIn("advanced research lab in Human-AI, directed by", desc)
        self.assertLessEqual(len(desc), 160)
        # not the old generic boilerplate
        self.assertNotIn("Human-Computer Interaction and AI directed by Professor", desc)

    def test_project_without_summary_falls_back_to_about(self):
        p = self.make_project(
            name="GlassEar", short_name="glassear", is_visible=True,
            start_date=date(2021, 1, 1), summary="",
            about="<p>GlassEar is a wearable sound-awareness display for d/Deaf users.</p>",
        )
        resp = self.client.get(reverse("website:project", args=[p.short_name]))
        desc = self._meta_description(resp)
        self.assertIn("GlassEar is a wearable sound-awareness display", desc)
        self.assertLessEqual(len(desc), 160)

    def test_project_without_summary_or_about_uses_trimmed_default(self):
        p = self.make_project(
            name="Empty Proj", short_name="emptyproj", is_visible=True,
            start_date=date(2021, 1, 1), summary="", about="",
        )
        resp = self.client.get(reverse("website:project", args=[p.short_name]))
        desc = self._meta_description(resp)
        # last-resort generic default — present but trimmed
        self.assertIn("Makeability Lab", desc)
        self.assertLessEqual(len(desc), 160)


class PageMetadataSchemeTests(DatabaseTestCase):
    """Absolute URLs follow ``request.scheme``. Behind UW CSE's TLS-terminating
    proxy that is https because ``SECURE_PROXY_SSL_HEADER`` trusts the proxy's
    ``X-Forwarded-Proto`` header (#1329, which replaced the DJANGO_ENV-keyed
    ``site_scheme`` workaround from #1236)."""

    @override_settings(SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"))
    def test_forwarded_proto_header_drives_https(self):
        """The deployed path: an http request carrying X-Forwarded-Proto: https
        is treated as secure, so absolute URLs emit https — exactly what Apache
        forwards to the container (#1329). This is the crux that the old
        DEBUG-based check got wrong on the test server (#1236)."""
        # Send a clean Host header too (as Apache does), so get_host() doesn't
        # append the test client's :80 port to the now-https URL.
        resp = self.client.get(
            reverse("website:index"),
            HTTP_X_FORWARDED_PROTO="https",
            HTTP_HOST="testserver",
        )
        self.assertContains(resp, '<link rel="canonical" href="https://testserver/">')
        self.assertContains(resp, '<meta property="og:url" content="https://testserver/">')

    def test_secure_request_uses_https(self):
        """A direct TLS request (request.scheme == https) emits https URLs."""
        resp = self.client.get(reverse("website:index"), secure=True)
        self.assertContains(resp, '<link rel="canonical" href="https://testserver/">')
        self.assertContains(resp, '<meta property="og:url" content="https://testserver/">')

    def test_local_dev_uses_request_scheme(self):
        """Local dev over http (no proxy header) follows request.scheme — http."""
        resp = self.client.get(reverse("website:index"))
        self.assertContains(resp, '<link rel="canonical" href="http://testserver/">')
        self.assertContains(resp, '<meta property="og:url" content="http://testserver/">')
