"""
Regression tests for the member page's artifact ordering and the AJAX
"See more" endpoint (issue #1110).

Covers:
  - get_member_projects(): visible projects ordered purely by most-recent
    artifact date (descending), no active/ended grouping, artifact-less projects
    last, invisible projects excluded. This pins the fix for the old bug where
    projects were ordered by the project's own start_date after being routed
    through an unordered set.
  - member_artifacts view: correct slicing, has_more / next_offset at the page
    boundaries, offset paging, defensive offset parsing, and 404s.
"""

from datetime import date

from django.urls import reverse

from website.models import ProjectRole
from website.views.member import (
    get_member_projects,
    ARTIFACT_PAGE_SIZES,
)

from .base import DatabaseTestCase


class MemberProjectOrderingTests(DatabaseTestCase):
    """get_member_projects() ordering and visibility filtering."""

    def _add_role(self, person, project):
        ProjectRole.objects.create(
            person=person, project=project, start_date=date(2024, 1, 1)
        )

    def test_projects_ordered_by_most_recent_artifact_descending(self):
        person = self.make_person()

        # An ACTIVE project (no end_date) whose newest artifact is old (2020).
        proj_active_old = self.make_project(name="Active Old", is_visible=True)
        pub_old = self.make_publication(title="Old Pub", year=2020)
        pub_old.projects.add(proj_active_old)

        # An ENDED project whose newest artifact is recent (2025).
        proj_ended_new = self.make_project(
            name="Ended New", is_visible=True, end_date=date(2024, 12, 31)
        )
        pub_new = self.make_publication(title="New Pub", year=2025)
        pub_new.projects.add(proj_ended_new)

        # A visible project with no artifacts at all -> sorts last.
        proj_no_artifacts = self.make_project(name="No Artifacts", is_visible=True)

        for proj in (proj_active_old, proj_ended_new, proj_no_artifacts):
            self._add_role(person, proj)

        ordered = get_member_projects(person)

        # Pure date order: the recently-active (ended) project outranks the
        # long-running active one because its artifact is newer. No active-first
        # grouping. Artifact-less project is last.
        self.assertEqual(
            ordered, [proj_ended_new, proj_active_old, proj_no_artifacts]
        )

    def test_invisible_projects_excluded(self):
        person = self.make_person()
        visible = self.make_project(name="Visible", is_visible=True)
        hidden = self.make_project(name="Hidden", is_visible=False)
        # Give the hidden project the newest artifact to prove visibility wins
        # over recency.
        hidden_pub = self.make_publication(title="Hidden Pub", year=2030)
        hidden_pub.projects.add(hidden)
        self._add_role(person, visible)
        self._add_role(person, hidden)

        ordered = get_member_projects(person)

        self.assertIn(visible, ordered)
        self.assertNotIn(hidden, ordered)


class MemberArtifactsEndpointTests(DatabaseTestCase):
    """The member_artifacts AJAX "See more" endpoint."""

    def _url(self, person, artifact_type, offset=None):
        url = reverse(
            "website:member_artifacts",
            kwargs={"member_id": person.id, "artifact_type": artifact_type},
        )
        if offset is not None:
            url += f"?offset={offset}"
        return url

    def setUp(self):
        super().setUp()
        self.person = self.make_person(first_name="Pagey", last_name="McTest")
        # 8 publications authored by the person; pubs page size is 6.
        self.pubs = []
        for i in range(8):
            pub = self.make_publication(title=f"Paper {i}", year=2024)
            pub.authors.add(self.person)
            self.pubs.append(pub)

    def test_first_page_reports_more(self):
        page_size = ARTIFACT_PAGE_SIZES["publications"]  # 6
        resp = self.client.get(self._url(self.person, "publications"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["has_more"])
        self.assertEqual(data["next_offset"], page_size)
        # The "Load more" path only exists for prolific members, who get the
        # VERTICAL list — so appended papers are vertical rows, not card-grid
        # cells (#1110).
        self.assertEqual(data["html"].count("pub-row-vert-layout"), page_size)
        self.assertNotIn("pub-column-horiz-layout", data["html"])

    def test_second_page_is_last(self):
        resp = self.client.get(self._url(self.person, "publications", offset=6))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["has_more"])
        self.assertEqual(data["next_offset"], 8)
        self.assertEqual(data["html"].count("pub-row-vert-layout"), 2)

    def test_offset_past_end_returns_empty(self):
        resp = self.client.get(self._url(self.person, "publications", offset=99))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["has_more"])
        self.assertEqual(data["html"], "")

    def test_load_all_returns_everything_from_offset(self):
        # ?all=1 returns every remaining item in one response (backs "Load all").
        resp = self.client.get(self._url(self.person, "publications") + "?all=1")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["has_more"])
        self.assertEqual(data["next_offset"], 8)
        self.assertEqual(data["html"].count("pub-row-vert-layout"), 8)

    def test_load_all_from_nonzero_offset(self):
        resp = self.client.get(self._url(self.person, "publications", offset=6) + "&all=1")
        data = resp.json()
        self.assertFalse(data["has_more"])
        self.assertEqual(data["html"].count("pub-row-vert-layout"), 2)

    def test_invalid_offset_treated_as_zero(self):
        resp = self.client.get(self._url(self.person, "publications", offset="abc"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # Falls back to offset 0 -> first full page.
        self.assertEqual(data["next_offset"], ARTIFACT_PAGE_SIZES["publications"])

    def test_unknown_artifact_type_404(self):
        resp = self.client.get(self._url(self.person, "widgets"))
        self.assertEqual(resp.status_code, 404)

    def test_unknown_member_404(self):
        url = reverse(
            "website:member_artifacts",
            kwargs={"member_id": 999999, "artifact_type": "publications"},
        )
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_talks_endpoint_renders_and_pages(self):
        person = self.make_person(first_name="Talky", last_name="One")
        for i in range(9):  # talks page size is 8
            talk = self.make_talk(title=f"Talk {i}", year=2024)
            talk.authors.add(person)

        first = self.client.get(self._url(person, "talks")).json()
        self.assertTrue(first["has_more"])
        self.assertEqual(first["next_offset"], 8)
        self.assertEqual(first["html"].count("talk-card"), 8)

        second = self.client.get(self._url(person, "talks", offset=8)).json()
        self.assertFalse(second["has_more"])
        self.assertEqual(second["html"].count("talk-card"), 1)

    def test_videos_endpoint_renders_and_pages(self):
        # A person's videos surface through an authored talk (or publication),
        # so wire each video to a talk the person gave. videos page size is 6.
        person = self.make_person(first_name="Viddy", last_name="One")
        for i in range(7):
            video = self.make_video(title=f"Video {i}", year=2024)
            talk = self.make_talk(title=f"Video Talk {i}", year=2024)
            talk.video = video
            talk.save()
            talk.authors.add(person)

        first = self.client.get(self._url(person, "videos")).json()
        self.assertTrue(first["has_more"])
        self.assertEqual(first["next_offset"], 6)
        self.assertEqual(first["html"].count("video-card"), 6)

        second = self.client.get(self._url(person, "videos", offset=6)).json()
        self.assertFalse(second["has_more"])
        self.assertEqual(second["html"].count("video-card"), 1)

    def test_projects_endpoint_pages_list_path(self):
        # Projects go through the Python-list code path (len()/slice) rather than
        # a queryset, so exercise it separately. 9 visible projects, page size 8.
        person = self.make_person(first_name="Proj", last_name="Owner")
        # Letters only: the project URL pattern (website:project) rejects digits
        # in short_name, and display_project_snippet.html reverses that URL.
        for i in range(9):
            letter = chr(ord("A") + i)
            proj = self.make_project(name=f"Project {letter}", is_visible=True)
            ProjectRole.objects.create(
                person=person, project=proj, start_date=date(2024, 1, 1)
            )

        first = self.client.get(self._url(person, "projects")).json()
        self.assertTrue(first["has_more"])
        self.assertEqual(first["next_offset"], 8)
        self.assertEqual(first["html"].count("project-card"), 8)

        second = self.client.get(self._url(person, "projects", offset=8)).json()
        self.assertFalse(second["has_more"])
        self.assertEqual(second["html"].count("project-card"), 1)


class MemberPageRenderTests(DatabaseTestCase):
    """End-to-end render of the member page with the #1110 changes wired in."""

    def test_page_renders_see_more_controls(self):
        person = self.make_person(first_name="Talky", last_name="McTest")
        # 9 talks > the talks page size (8): collapsible grid + See More controls.
        for i in range(9):
            talk = self.make_talk(title=f"Talk {i}", year=2024)
            talk.authors.add(person)

        resp = self.client.get(
            reverse("website:member_by_name", kwargs={"member_name": person.url_name})
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode()
        # The talks grid is collapsible and the load-more controls are present
        # (rendered hidden; JS un-hides them and sets exact counts).
        self.assertIn('id="person-talks-grid"', body)
        self.assertIn("is-collapsed", body)
        self.assertIn("see-more-controls", body)
        self.assertIn('data-artifact-type="talks"', body)
        self.assertIn("Load more talks", body)
        self.assertIn("Load all talks", body)
        # Headings never say "Recent" any more; they carry a loaded/total count
        # (8 of 9 loaded) instead. (Check the old heading string specifically —
        # the page footer has an unrelated "Recent News" block.)
        self.assertNotIn("Recent Talks", body)
        self.assertIn("person-section-count", body)
        self.assertIn("(8/9)", body)
        # The bio-expand / load-more scripts are wired up.
        self.assertIn("member-load-more.js", body)
        self.assertIn("bio-expand.js", body)

    def _get_member_body(self, person):
        resp = self.client.get(
            reverse("website:member_by_name", kwargs={"member_name": person.url_name})
        )
        self.assertEqual(resp.status_code, 200)
        return resp.content.decode()

    def _make_pubs(self, person, n):
        for i in range(n):
            pub = self.make_publication(title=f"Paper {i}", year=2024)
            pub.authors.add(person)

    def test_section_nav_lists_only_present_sections(self):
        # The sticky section nav links only to sections that exist (#1110).
        person = self.make_person(first_name="Nav", last_name="Tester")
        for i in range(2):
            talk = self.make_talk(title=f"Talk {i}", year=2024)
            talk.authors.add(person)
        body = self._get_member_body(person)
        self.assertIn("member-section-nav", body)
        self.assertIn("member-nav.js", body)
        self.assertIn('data-section-link="person-talks"', body)
        self.assertNotIn('data-section-link="person-videos"', body)
        self.assertNotIn('data-section-link="person-publications"', body)
        self.assertNotIn('data-section-link="person-projects"', body)
        # The nav carries the person's name (revealed on scroll by JS) and a
        # loaded/total count per section (2 talks shown of 2 total).
        self.assertIn("member-section-nav-name", body)
        self.assertIn(person.get_full_name(), body)
        self.assertIn("member-section-nav-count", body)
        self.assertIn("(2/2)", body)

    def test_nav_count_reflects_loaded_slice_over_total(self):
        # 9 talks: the desktop slice (8) is loaded, of 9 total -> "(8/9)".
        person = self.make_person(first_name="Count", last_name="Tester")
        for i in range(9):
            talk = self.make_talk(title=f"Talk {i}", year=2024)
            talk.authors.add(person)
        body = self._get_member_body(person)
        self.assertIn("(8/9)", body)

    def test_few_publications_use_vertical_layout_without_controls(self):
        # <= 3 papers: vertical list, no controls (a grid of 1-3 looks sparse).
        person = self.make_person(first_name="Fewpubs", last_name="McTest")
        self._make_pubs(person, 2)
        body = self._get_member_body(person)
        self.assertEqual(body.count("pub-row-vert-layout"), 2)
        self.assertNotIn("pub-column-horiz-layout", body)
        self.assertNotIn('data-artifact-type="publications"', body)
        self.assertNotIn("Recent Papers", body)

    def test_mid_count_publications_use_card_grid_without_controls(self):
        # 4..page_size papers: compact horizontal card grid, still no paging.
        person = self.make_person(first_name="Midpubs", last_name="McTest")
        self._make_pubs(person, 5)  # 3 < 5 <= 6
        body = self._get_member_body(person)
        self.assertEqual(body.count("pub-column-horiz-layout"), 5)
        self.assertNotIn("pub-row-vert-layout", body)
        self.assertIn("person-publications-grid", body)
        self.assertNotIn('data-artifact-type="publications"', body)
        self.assertNotIn("Recent Papers", body)

    def test_many_publications_use_vertical_list_with_controls(self):
        # > page_size papers: scannable vertical list + Load more/all controls.
        person = self.make_person(first_name="Manypubs", last_name="McTest")
        self._make_pubs(person, 7)  # > 6
        body = self._get_member_body(person)
        self.assertIn('id="person-publications-grid"', body)
        self.assertIn("person-publications-list", body)  # vertical, not card grid
        self.assertEqual(body.count("pub-row-vert-layout"), 6)  # desktop page size
        self.assertNotIn("pub-column-horiz-layout", body)
        self.assertIn("see-more-controls", body)
        self.assertIn('data-artifact-type="publications"', body)
        self.assertIn("Load more papers", body)
        self.assertIn("Load all papers", body)
        # No "Recent" prefix; the heading carries a loaded/total count (6 of 7).
        self.assertNotIn("Recent Papers", body)
        self.assertIn("(6/7)", body)
