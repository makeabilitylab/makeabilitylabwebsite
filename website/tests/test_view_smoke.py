"""
View smoke-sweep: GET every public page route and assert it renders (#1278, item 5).

The cheap, high-yield test the issue calls for. It doesn't check page *content*
-- it checks that each public URL resolves, the view runs, and the template
renders without blowing up. That catches a whole class of regressions that unit
tests miss because they only surface through the real URL/view/template stack:
NoReverseMatch from a renamed url name, AttributeError from a template touching a
field that moved, a context key a partial expects but the view stopped passing.

Routes are built with ``reverse()`` so a renamed url name fails here too (rather
than silently skipping the route). The two media routes (serve_pdf,
serve_publication_image) are intentionally excluded -- they need real files on
disk and already have dedicated tests (test_serve_pdf, test_serve_publication_image).

The fixtures form a small connected graph (a person who authored a publication
and a talk, both tied to a visible project they have a role on, plus a news item)
so the listing and detail templates exercise their populated branches, not just
the empty-state ones.
"""

from datetime import date

from website.tests.base import DatabaseTestCase
from website.tests.factories import ProjectRoleFactory

from django.urls import reverse


# Public page routes that take no arguments. view_project_people is an AJAX-y
# endpoint but is a plain GET that returns a rendered template, so it sweeps here.
STATIC_ROUTE_NAMES = [
    "index",
    "people",
    "publications",
    "awards",
    "projects",
    "news_listing",
    "view_project_people",
]

# member_artifacts serves one section at a time; these are the valid types
# (anything else is a deliberate 404 -- see member.py::ARTIFACT_PAGE_SIZES).
MEMBER_ARTIFACT_TYPES = ["projects", "publications", "videos", "talks"]


class PublicViewSmokeTests(DatabaseTestCase):
    """GET every public page route and assert a 200 (catches the template bug class)."""

    def setUp(self):
        super().setUp()
        self.person = self.make_person(first_name="Smoke", last_name="Tester")
        # start_date set so the page renders the normal "2022–Present" date
        # string; the null-start_date edge case is pinned in test_project.py.
        self.project = self.make_project(
            name="Smoke Project", is_visible=True, start_date=date(2022, 1, 1)
        )

        # A publication + talk authored by the person and tied to the project,
        # so member/project/listing templates render their populated branches.
        self.pub = self.make_publication(title="Smoke Paper", authors=[self.person])
        self.pub.projects.add(self.project)
        self.talk = self.make_talk(title="Smoke Talk", authors=[self.person])

        # A role so the project has a member (drives view_project_people + the
        # member page's project section).
        ProjectRoleFactory(person=self.person, project=self.project)

        self.news = self.make_news_item(title="Smoke News", author=self.person)

    def _assert_ok(self, url):
        response = self.client.get(url)
        self.assertEqual(
            response.status_code, 200,
            f"GET {url} returned {response.status_code}, expected 200",
        )
        return response

    def test_static_pages_render(self):
        for name in STATIC_ROUTE_NAMES:
            with self.subTest(route=name):
                self._assert_ok(reverse(f"website:{name}"))

    def test_member_page_by_id_and_by_name(self):
        self._assert_ok(
            reverse("website:member_by_id", kwargs={"member_id": self.person.id})
        )
        self._assert_ok(
            reverse(
                "website:member_by_name",
                kwargs={"member_name": self.person.url_name},
            )
        )

    def test_member_artifacts_all_types(self):
        for artifact_type in MEMBER_ARTIFACT_TYPES:
            with self.subTest(artifact_type=artifact_type):
                self._assert_ok(
                    reverse(
                        "website:member_artifacts",
                        kwargs={
                            "member_id": self.person.id,
                            "artifact_type": artifact_type,
                        },
                    )
                )

    def test_project_detail_page(self):
        self._assert_ok(
            reverse(
                "website:project",
                kwargs={"project_name": self.project.short_name},
            )
        )

    def test_news_item_by_id_and_by_slug(self):
        self._assert_ok(
            reverse("website:news_item_by_id", kwargs={"id": self.news.id})
        )
        self._assert_ok(
            reverse(
                "website:news_item_by_slug", kwargs={"slug": self.news.slug}
            )
        )
