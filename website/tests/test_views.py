"""
View / template / queryset regression tests.

These exercise the URL → view → template stack end to end (or render snippets
directly), catching the class of bugs that pure unit tests can't — template
crashes, NoReverseMatch, and N+1 query regressions.
"""

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from website.tests.base import DatabaseTestCase


# --- View-level: null author on /news/<id>/ (regression for #1013) --------


class NewsItemNullAuthorViewTests(DatabaseTestCase):
    """
    Regression for #1013 — a News item with author=None used to crash the
    news_item view with AttributeError on cur_news_item.author.authored_news.
    Fixed in 1c0d6c0 by guarding the access. This test pins the behavior
    so it can't regress silently.
    """

    def test_news_item_with_null_author_renders_200(self):
        item = self.make_news_item(title="Authorless News", author=None)
        response = self.client.get(
            reverse("website:news_item_by_id", kwargs={"id": item.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Authorless News")

    def test_news_item_with_author_still_renders_200(self):
        """Sanity check: the non-null path also works."""
        author = self.make_person(first_name="Ada", last_name="Lovelace")
        item = self.make_news_item(
            title="Authored News", author=author
        )
        response = self.client.get(
            reverse("website:news_item_by_id", kwargs={"id": item.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Authored News")


# --- Talk snippet: external_slides_url rendering (#1273) -----------------


class TalkExternalSlidesUrlTests(DatabaseTestCase):
    """
    Pins the rendering of Talk.external_slides_url in
    snippets/display_talk_snippet.html — the "Source" link should appear
    only when the URL is set. Also pins that Poster persists the field
    (no display surface for posters yet, but the column must exist).
    """

    def _render_talk_snippet(self, talk):
        from django.template.loader import render_to_string
        return render_to_string(
            "snippets/display_talk_snippet.html",
            {"talk": talk, "MEDIA_URL": "/media/"},
        )

    def test_source_link_renders_when_external_slides_url_set(self):
        talk = self.make_talk(
            title="Figma Talk",
            external_slides_url="https://www.figma.com/file/abc123/slides",
        )
        html = self._render_talk_snippet(talk)
        self.assertIn("https://www.figma.com/file/abc123/slides", html)
        self.assertIn("fa-up-right-from-square", html)
        # opens-in-new-tab affordance must be present for accessibility
        self.assertIn('target="_blank"', html)
        self.assertIn('rel="noopener"', html)

    def test_source_link_absent_when_external_slides_url_blank(self):
        talk = self.make_talk(title="No-Source Talk")
        html = self._render_talk_snippet(talk)
        self.assertNotIn("fa-up-right-from-square", html)

    def test_poster_external_slides_url_round_trips(self):
        """Schema pin: Poster.external_slides_url must persist to the DB."""
        from website.models import Poster
        poster = Poster.objects.create(
            title="A Test Poster",
            external_slides_url="https://www.figma.com/file/xyz/poster",
            pdf_file=SimpleUploadedFile(
                "test_poster.pdf",
                b"%PDF-1.4 test",
                content_type="application/pdf",
            ),
        )
        reloaded = Poster.objects.get(pk=poster.pk)
        self.assertEqual(
            reloaded.external_slides_url,
            "https://www.figma.com/file/xyz/poster",
        )


# --- Query-count: /publications/ prefetch_related (regression for d4f6d65) -


class PublicationsViewQueryCountTests(DatabaseTestCase):
    """
    Pins the prefetch_related batch on /publications/ (d4f6d65).

    Before the fix, the snippet template iterated pub.authors.all and
    pub.projects.all per publication, producing 617 queries on prod with
    ~250 pubs. The fix added .prefetch_related('authors', 'projects',
    'keywords') to the view's queryset, dropping that to 60.

    The key correctness property is that the query count is bounded by a
    constant — it must NOT grow with the number of publications. This
    test creates publications with M2M relations and asserts the count
    stays under a generous ceiling for two different data sizes. If a
    future contributor removes the prefetches, the count climbs linearly
    and the larger-N test fails.
    """

    # Generous ceiling well above the steady-state count we measured
    # locally (~15 queries for the publications view). The ceiling exists
    # to catch order-of-magnitude regressions, not to pin an exact count.
    QUERY_CEILING = 30

    def _seed_publications(self, count):
        author = self.make_person(first_name="Ada", last_name="Lovelace")
        for i in range(count):
            pub = self.make_publication(
                title=f"Paper {i}", year=2024
            )
            pub.authors.add(author)

    def _capture_publications_query_count(self):
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(reverse("website:publications"))
        return response, len(ctx.captured_queries)

    def test_query_count_is_bounded_with_few_pubs(self):
        self._seed_publications(2)
        response, count = self._capture_publications_query_count()
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(
            count,
            self.QUERY_CEILING,
            msg=f"Query count {count} exceeded ceiling {self.QUERY_CEILING}",
        )

    def test_query_count_does_not_grow_with_pub_count(self):
        """
        The real regression guard: query count must be roughly the same
        whether we render 2 pubs or 20. If prefetches are removed, the
        count grows by a multiple of N and this test will fail.
        """
        self._seed_publications(20)
        response, count = self._capture_publications_query_count()
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(
            count,
            self.QUERY_CEILING,
            msg=(
                f"Query count {count} exceeded ceiling {self.QUERY_CEILING} "
                "with 20 publications — prefetch_related likely regressed"
            ),
        )


# --- Member ORCID / Google Scholar profile links (#1324) -----------------


class MemberSocialLinkTests(DatabaseTestCase):
    """
    Pins the ORCID + Google Scholar fields added to Person: that
    has_website_links() recognizes them and that the member page renders the
    links (academicons icons) when set.
    """

    def _give_position(self, person):
        from datetime import date
        from website.models import Position
        from website.models.position import Title
        Position.objects.create(person=person, start_date=date(2020, 1, 1),
                                title=Title.PHD_STUDENT)

    def test_has_website_links_true_with_only_scholar_or_orcid(self):
        p = self.make_person(first_name="Onlyorcid", last_name="Person",
                             orcid="https://orcid.org/0000-0002-1853-9710")
        self.assertTrue(p.has_website_links())
        p2 = self.make_person(first_name="Onlyscholar", last_name="Person",
                              google_scholar="https://scholar.google.com/citations?user=lFn1Oz0AAAAJ")
        self.assertTrue(p2.has_website_links())

    def test_has_website_links_false_with_no_links(self):
        p = self.make_person(first_name="Nolinks", last_name="Person")
        self.assertFalse(p.has_website_links())

    def test_member_page_renders_orcid_and_scholar(self):
        person = self.make_person(
            first_name="Linked", last_name="Person",
            orcid="https://orcid.org/0000-0002-1853-9710",
            google_scholar="https://scholar.google.com/citations?user=lFn1Oz0AAAAJ",
        )
        self._give_position(person)
        resp = self.client.get(
            reverse("website:member_by_name", kwargs={"member_name": person.url_name})
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'href="https://orcid.org/0000-0002-1853-9710"')
        self.assertContains(resp, 'ai ai-orcid')
        self.assertContains(resp, "scholar.google.com/citations?user=lFn1Oz0AAAAJ")
        self.assertContains(resp, 'ai ai-google-scholar')
