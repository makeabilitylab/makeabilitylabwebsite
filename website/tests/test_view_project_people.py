"""
Regression tests for the internal "view project people" page
(:func:`website.views.view_project_people.view_project_people`).

This page builds a JSON payload of every Person plus per-project role data and
renders an entirely client-side grid (used to generate acknowledgment slides for
talks). These tests lock the contract of that payload — project-role aggregation,
director identification (by name, via ``Person.get_director()``), PhD-advisee
flagging, and the publication indicators — so the view can be refactored safely.
"""

import json
from datetime import date, timedelta

from django.urls import reverse

from website.models import Person, Project, Publication
from website.models.position import Position, Role, Title
from website.models.project_role import ProjectRole
from website.models.publication import PubType
from website.tests.base import DatabaseTestCase


class ViewProjectPeopleTests(DatabaseTestCase):
    """Integration tests that exercise the real view, queryset, and template."""

    def _get_people_by_id(self):
        """GET the page and return (response, {person_id: person_payload})."""
        response = self.client.get(reverse("website:view_project_people"))
        self.assertEqual(response.status_code, 200)
        people = json.loads(response.context["people_json"])
        return response, {p["id"]: p for p in people}

    def _add_position(self, person, title, start, end=None, **kwargs):
        """Create a Position for `person` (Member role unless overridden)."""
        kwargs.setdefault("role", Role.MEMBER)
        return Position.objects.create(
            person=person, title=title, start_date=start, end_date=end, **kwargs
        )

    def test_page_renders_and_payloads_parse(self):
        """The view returns 200 and all three context JSON blobs are valid JSON."""
        person = self.make_person(first_name="Ada", last_name="Lovelace")
        self._add_position(person, Title.PHD_STUDENT, date(2020, 1, 1))

        response = self.client.get(reverse("website:view_project_people"))
        self.assertEqual(response.status_code, 200)
        for key in ("people_json", "projects_json", "abstracted_titles_json"):
            parsed = json.loads(response.context[key])
            self.assertIsInstance(parsed, list)

    def test_project_role_aggregation(self):
        """project_roles aggregates total days and start/end dates per project."""
        person = self.make_person(first_name="Grace", last_name="Hopper")
        self._add_position(person, Title.PHD_STUDENT, date(2019, 1, 1))
        project = Project.objects.create(name="Test Project", short_name="TestProj")
        start, end = date(2020, 1, 1), date(2020, 12, 31)
        ProjectRole.objects.create(
            person=person, project=project, start_date=start, end_date=end
        )

        _, people = self._get_people_by_id()
        roles = people[person.id]["project_roles"]
        self.assertIn("TestProj", roles)
        self.assertEqual(roles["TestProj"]["total_days"], (end - start).days)
        self.assertEqual(roles["TestProj"]["start_date"], "2020-01-01")
        self.assertEqual(roles["TestProj"]["end_date"], "2020-12-31")

    def test_director_flagged_by_name(self):
        """is_director is true only for the canonical director (Person.get_director())."""
        first, last = Person.DIRECTOR_NAME
        director = self.make_person(first_name=first, last_name=last)
        self._add_position(director, Title.FULL_PROF, date(2010, 1, 1))
        other = self.make_person(first_name="Reg", last_name="Ular")
        self._add_position(other, Title.PHD_STUDENT, date(2020, 1, 1))

        _, people = self._get_people_by_id()
        self.assertTrue(people[director.id]["is_director"])
        self.assertFalse(people[other.id]["is_director"])

    def test_director_resolved_when_holding_professor_title(self):
        """
        Regression for #1284: in production the lab director holds a professor
        title (not a ``Title.DIRECTOR`` position), and other people hold professor
        titles too (collaborators). The director — and therefore the PhD-advisee
        set the "Only my PhD advisees" filter relies on — must still resolve to the
        canonical director and no one else.
        """
        # Another professor who is not the director and must not be flagged.
        other_prof = self.make_person(first_name="Alice", last_name="Collaborator")
        self._add_position(other_prof, Title.FULL_PROF, date(2010, 1, 1))

        first, last = Person.DIRECTOR_NAME
        director = self.make_person(first_name=first, last_name=last)
        self._add_position(director, Title.FULL_PROF, date(2010, 1, 1))

        advisee = self.make_person(first_name="Phd", last_name="Student")
        self._add_position(advisee, Title.PHD_STUDENT, date(2022, 1, 1), advisor=director)

        _, people = self._get_people_by_id()
        self.assertTrue(people[director.id]["is_director"])
        self.assertFalse(people[other_prof.id]["is_director"])
        self.assertTrue(people[advisee.id]["is_phd_advisee"])

    def test_phd_advisee_logic_matches_model(self):
        """
        is_phd_advisee mirrors Person.is_phd_advisee_of: current advisee -> true,
        past advisee without dissertation -> false, past advisee with one -> true.
        """
        first, last = Person.DIRECTOR_NAME
        director = self.make_person(first_name=first, last_name=last)
        self._add_position(director, Title.FULL_PROF, date(2010, 1, 1))

        current = self.make_person(first_name="Cur", last_name="Rent")
        self._add_position(current, Title.PHD_STUDENT, date(2022, 1, 1), advisor=director)

        past = date.today() - timedelta(days=400)
        past_no_diss = self.make_person(first_name="Past", last_name="Nodiss")
        self._add_position(
            past_no_diss, Title.PHD_STUDENT, date(2015, 1, 1), end=past, advisor=director
        )

        past_with_diss = self.make_person(first_name="Past", last_name="Withdiss")
        self._add_position(
            past_with_diss, Title.PHD_STUDENT, date(2015, 1, 1), end=past, co_advisor=director
        )
        dissertation = self.make_publication(
            title="A Dissertation", pub_venue_type=PubType.PHD_DISSERTATION
        )
        dissertation.authors.add(past_with_diss)

        _, people = self._get_people_by_id()
        self.assertTrue(people[current.id]["is_phd_advisee"])
        self.assertFalse(people[past_no_diss.id]["is_phd_advisee"])
        self.assertTrue(people[past_with_diss.id]["is_phd_advisee"])
        # Sanity-check against the canonical model method.
        self.assertEqual(
            people[current.id]["is_phd_advisee"], current.is_phd_advisee_of(director)
        )
        self.assertEqual(
            people[past_no_diss.id]["is_phd_advisee"],
            past_no_diss.is_phd_advisee_of(director),
        )

    def test_publication_indicators(self):
        """has_any_publication and projects_published_on reflect authored pubs."""
        project = Project.objects.create(name="Pub Project", short_name="PubProj")
        author = self.make_person(first_name="Wri", last_name="Ter")
        self._add_position(author, Title.PHD_STUDENT, date(2020, 1, 1))
        pub = self.make_publication(title="Authored Paper")
        pub.authors.add(author)
        pub.projects.add(project)

        non_author = self.make_person(first_name="Non", last_name="Author")
        self._add_position(non_author, Title.UGRAD, date(2021, 1, 1))

        _, people = self._get_people_by_id()
        self.assertTrue(people[author.id]["has_any_publication"])
        self.assertIn("PubProj", people[author.id]["projects_published_on"])
        self.assertFalse(people[non_author.id]["has_any_publication"])
        self.assertEqual(people[non_author.id]["projects_published_on"], [])
