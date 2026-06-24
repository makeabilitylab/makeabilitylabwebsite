"""
Regression tests for the mobile project-page metadata blocks (#1271).

The individual project page (`website/templates/website/project.html`) renders a
mobile-only metadata treatment that replaces the old auto-fit sidebar grid:

  * a compact chip row under the title (status / date range / contributor count),
  * a labeled info list (Links as clickable chips, Team, Funding),
  * a "Team" list that shows the first few leads and collapses the rest into a
    native ``<details>`` disclosure ("+N more").

These blocks are mobile-only (CSS hides them ≥992px) but they are always present
in the rendered HTML, so we can assert on the markup here. The desktop sidebar
(`.project-sidebar`) must keep rendering unchanged. See #1271.
"""

from datetime import date

from django.urls import reverse

from website.models import Grant, ProjectRole, Sponsor
from website.models.project_role import LeadProjectRoleTypes
from website.tests.base import DatabaseTestCase
from website.tests.factories import image_upload


class ProjectPageMobileMetaTests(DatabaseTestCase):
    """Renders a fully-populated, visible project and asserts the mobile blocks."""

    # The Team list shows this many leads before collapsing the rest into
    # <details>. Kept in sync with project.html's slice value.
    VISIBLE_LEADS = 4

    def setUp(self):
        # Ongoing (no end_date) → "Active"; start in 2021 → date range "2021–Present".
        self.project = self.make_project(
            name="Project Sidewalk",
            short_name="sidewalk",
            is_visible=True,
            start_date=date(2021, 1, 1),
            website="https://example.org/sidewalk",
            data_url="https://example.org/sidewalk/data",
        )

        # 1 PI + 6 student leads = 7 leads, which exceeds VISIBLE_LEADS so the
        # "+N more" <details> overflow is exercised.
        self.pi = self.make_person(first_name="Jon", last_name="Froehlich")
        ProjectRole.objects.create(
            person=self.pi, project=self.project,
            lead_project_role=LeadProjectRoleTypes.PI, start_date=date(2021, 1, 1),
        )
        self.leads = []
        for i in range(6):
            person = self.make_person(first_name=f"Lead{i}", last_name="Student")
            ProjectRole.objects.create(
                person=person, project=self.project,
                lead_project_role=LeadProjectRoleTypes.STUDENT_LEAD,
                start_date=date(2021, 1, 1),
            )
            self.leads.append(person)

        # One sponsor via a grant so the Funding row renders.
        sponsor = Sponsor.objects.create(
            name="Demo Science Foundation", short_name="DSF",
            url="https://example.org/dsf", alt_text="DSF logo",
            icon=image_upload("dsf_icon.gif"),
        )
        grant = Grant.objects.create(
            title="Demo Grant: sidewalk", sponsor=sponsor, date=date(2021, 1, 1),
        )
        grant.projects.add(self.project)

        self.url = reverse("website:project", args=[self.project.short_name])

    def _get(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def test_mobile_meta_block_renders(self):
        html = self._get()
        self.assertIn("project-mobile-meta", html)

    def test_status_chip_shows_active_for_ongoing_project(self):
        html = self._get()
        self.assertIn("project-meta-chips", html)
        self.assertIn("Active", html)

    def test_chips_show_date_range_and_contributor_count(self):
        html = self._get()
        # Ongoing project starting 2021 → "2021–Present".
        self.assertIn("2021", html)
        # 7 people in roles → contributor count chip.
        self.assertIn("contributor", html.lower())

    def test_links_render_as_clickable_chips(self):
        html = self._get()
        self.assertIn("project-meta-link", html)
        self.assertIn("https://example.org/sidewalk", html)
        self.assertIn("https://example.org/sidewalk/data", html)

    def test_team_overflow_collapses_into_details(self):
        html = self._get()
        # The PI is among the always-visible leads.
        self.assertIn("Jon Froehlich", html)
        # With 7 leads > VISIBLE_LEADS, the overflow disclosure must appear.
        self.assertIn("project-team-more", html)
        self.assertIn("<details", html)

    def test_funding_row_renders_sponsor(self):
        html = self._get()
        self.assertIn("Demo Science Foundation", html)

    def test_desktop_sidebar_still_renders(self):
        html = self._get()
        # The desktop sidebar is untouched by the mobile redesign.
        self.assertIn("project-sidebar", html)


class ProjectPageMobileMetaEmptyTests(DatabaseTestCase):
    """A sparse project (no leads, links, or sponsors) must still render cleanly."""

    def test_page_renders_without_optional_metadata(self):
        project = self.make_project(
            name="Bare Project", short_name="bare", is_visible=True,
            start_date=date(2020, 1, 1), end_date=date(2022, 1, 1),
        )
        url = reverse("website:project", args=[project.short_name])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        # Ended project → "Completed" status, no Team overflow disclosure.
        self.assertIn("Completed", html)
        self.assertNotIn("project-team-more", html)
