"""
Integration tests for the public read-only REST API (#1268).

Exercises the real URL/view/serializer stack through Django's test client so the
API contract (endpoints, filters, pagination, visibility gating, absolute URLs,
CORS) is pinned against regressions. Uses the shared DatabaseTestCase fixtures
plus a few direct model creates for the relationships the factories don't cover
(Position, Sponsor/Grant, ProjectRole leadership).
"""

from datetime import date

from website.models import Grant, Position, ProjectRole, Sponsor
from website.models.position import Title
from website.models.project_role import LeadProjectRoleTypes
from website.models.publication import PubType
from website.tests.base import DatabaseTestCase


class ApiTestCase(DatabaseTestCase):
    def setUp(self):
        # A visible project (Project Sidewalk) and a hidden one.
        self.project = self.make_project(
            name="Project Sidewalk", short_name="projectsidewalk", is_visible=True
        )
        self.hidden_project = self.make_project(
            name="Secret Project", short_name="secretproj", is_visible=False
        )

        # Jon is a lab member (has a Position) and PI on the project.
        self.jon = self.make_person(first_name="Jon", last_name="Froehlich")
        Position.objects.create(
            person=self.jon, start_date=date(2012, 1, 1), title=Title.FULL_PROF
        )
        ProjectRole.objects.create(
            person=self.jon,
            project=self.project,
            start_date=date(2012, 1, 1),
            lead_project_role=LeadProjectRoleTypes.PI,
        )
        # Jon also held a *past* (ended) Co-PI role. Even though he's currently
        # an active PI, this past lead role must still surface in leadership --
        # the case Project.get_project_leadership() drops (per-person "inactive").
        ProjectRole.objects.create(
            person=self.jon,
            project=self.project,
            start_date=date(2010, 1, 1),
            end_date=date(2011, 12, 31),
            lead_project_role=LeadProjectRoleTypes.CO_PI,
        )
        # A person who was only ever a past student lead (role ended).
        self.past_lead = self.make_person(first_name="Past", last_name="Lead")
        ProjectRole.objects.create(
            person=self.past_lead,
            project=self.project,
            start_date=date(2013, 1, 1),
            end_date=date(2016, 1, 1),
            lead_project_role=LeadProjectRoleTypes.STUDENT_LEAD,
        )

        # An external co-author with NO Position -> should not appear in /people/.
        self.coauthor = self.make_person(first_name="Ext", last_name="Author")

        # Six conference pubs authored by Jon and attached to the project
        # (years 2018..2023), plus one unrelated journal pub by the co-author.
        self.project_pubs = []
        for year in range(2018, 2024):
            pub = self.make_publication(
                title=f"Sidewalk Paper {year}", year=year, authors=[self.jon]
            )
            pub.projects.add(self.project)
            self.project_pubs.append(pub)

        self.other_pub = self.make_publication(
            title="Unrelated Journal Paper",
            year=2024,
            authors=[self.coauthor],
            pub_venue_type=PubType.JOURNAL,
        )

        # A grant funding the project.
        self.sponsor = Sponsor.objects.create(name="National Science Foundation",
                                               short_name="NSF")
        self.grant = Grant.objects.create(
            title="NSF Award for Sidewalk",
            sponsor=self.sponsor,
            date=date(2015, 1, 1),
            funding_amount=500000,
            grant_id="1302338",
        )
        self.grant.projects.add(self.project)

    # ---- publications list: filtering, ordering, pagination -----------------

    def test_publications_list_returns_all(self):
        resp = self.client.get("/api/v1/publications/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 7)

    def test_publications_pagination_page_size(self):
        resp = self.client.get("/api/v1/publications/?page_size=5")
        body = resp.json()
        self.assertEqual(body["count"], 7)
        self.assertEqual(len(body["results"]), 5)

    def test_publications_default_ordering_newest_first(self):
        results = self.client.get("/api/v1/publications/").json()["results"]
        self.assertEqual(results[0]["year"], 2024)  # the 2024 journal paper

    def test_publications_filter_by_author(self):
        resp = self.client.get(f"/api/v1/publications/?author={self.jon.url_name}")
        body = resp.json()
        self.assertEqual(body["count"], 6)
        titles = {r["title"] for r in body["results"]}
        self.assertNotIn("Unrelated Journal Paper", titles)

    def test_publications_filter_by_project(self):
        resp = self.client.get("/api/v1/publications/?project=projectsidewalk")
        self.assertEqual(resp.json()["count"], 6)

    def test_publications_filter_by_year(self):
        resp = self.client.get("/api/v1/publications/?year=2023")
        self.assertEqual(resp.json()["count"], 1)

    def test_publications_filter_by_type(self):
        self.assertEqual(
            self.client.get("/api/v1/publications/?type=Journal").json()["count"], 1
        )
        self.assertEqual(
            self.client.get("/api/v1/publications/?type=Conference").json()["count"], 6
        )

    def test_publication_detail_has_bibtex(self):
        pub = self.project_pubs[0]
        resp = self.client.get(f"/api/v1/publications/{pub.id}/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("bibtex", resp.json())

    def test_publication_urls_are_absolute(self):
        results = self.client.get("/api/v1/publications/").json()["results"]
        pub = results[0]
        self.assertTrue(pub["pdf_url"].startswith("http://"))
        # nested author page URL is absolute and points at /member/
        author_url = pub["authors"][0]["url"]
        self.assertTrue(author_url.startswith("http://"))
        self.assertIn("/member/", author_url)

    # ---- projects list + visibility gating ----------------------------------

    def test_projects_list_excludes_hidden(self):
        results = self.client.get("/api/v1/projects/").json()["results"]
        short_names = {p["short_name"] for p in results}
        self.assertIn("projectsidewalk", short_names)
        self.assertNotIn("secretproj", short_names)

    def test_hidden_project_detail_404(self):
        self.assertEqual(self.client.get("/api/v1/projects/secretproj/").status_code, 404)

    def test_unknown_project_detail_404(self):
        self.assertEqual(self.client.get("/api/v1/projects/nope/").status_code, 404)

    # ---- project sub-resources ----------------------------------------------

    def test_project_publications_subresource(self):
        resp = self.client.get("/api/v1/projects/projectsidewalk/publications/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 6)

    def test_project_grants_subresource(self):
        resp = self.client.get("/api/v1/projects/projectsidewalk/grants/")
        body = resp.json()
        self.assertEqual(body["count"], 1)
        grant = body["results"][0]
        self.assertEqual(grant["sponsor"]["short_name"], "NSF")
        self.assertEqual(grant["funding_amount"], 500000)

    def test_project_people_subresource(self):
        resp = self.client.get("/api/v1/projects/projectsidewalk/people/")
        body = resp.json()
        # 3 roles: Jon's PI + Jon's past Co-PI + Past Lead's student-lead role.
        self.assertEqual(body["count"], 3)
        names = {r["person"]["name"] for r in body["results"]}
        self.assertEqual(names, {"Jon Froehlich", "Past Lead"})
        lead_roles = {r["lead_project_role"] for r in body["results"]}
        self.assertEqual(lead_roles, {"PI", "Co-PI", "Student Lead"})

    def test_project_leadership_subresource(self):
        resp = self.client.get("/api/v1/projects/projectsidewalk/leadership/")
        body = resp.json()
        pi_names = {r["person"]["name"] for r in body["pis"]}
        self.assertIn("Jon Froehlich", pi_names)

    def test_project_leadership_includes_all_time(self):
        """Leadership spans current AND past roles, including past roles held by
        someone who is currently active in another capacity."""
        body = self.client.get(
            "/api/v1/projects/projectsidewalk/leadership/"
        ).json()

        # Jon's past Co-PI role appears even though he's a current PI.
        copi = body["co_pis"]
        self.assertEqual(len(copi), 1)
        self.assertEqual(copi[0]["person"]["name"], "Jon Froehlich")
        self.assertFalse(copi[0]["is_active"])

        # A person whose only role was a past student lead still appears.
        leads = body["student_leads"]
        self.assertEqual({r["person"]["name"] for r in leads}, {"Past Lead"})
        self.assertFalse(leads[0]["is_active"])

    # ---- people -------------------------------------------------------------

    def test_people_list_scoped_to_members(self):
        results = self.client.get("/api/v1/people/").json()["results"]
        names = {p["name"] for p in results}
        self.assertIn("Jon Froehlich", names)  # has a Position
        self.assertNotIn("Ext Author", names)  # co-author only, no Position

    def test_person_detail_by_url_name(self):
        resp = self.client.get(f"/api/v1/people/{self.jon.url_name}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["name"], "Jon Froehlich")

    def test_person_email_not_exposed(self):
        resp = self.client.get(f"/api/v1/people/{self.jon.url_name}/")
        self.assertNotIn("email", resp.json())

    # ---- CORS ---------------------------------------------------------------

    def test_cors_header_present_on_api(self):
        resp = self.client.get("/api/v1/publications/")
        self.assertEqual(resp["Access-Control-Allow-Origin"], "*")

    def test_cors_header_absent_off_api(self):
        resp = self.client.get("/version.json")
        self.assertNotIn("Access-Control-Allow-Origin", resp)

    def test_cors_options_preflight(self):
        resp = self.client.options("/api/v1/publications/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Access-Control-Allow-Origin"], "*")
