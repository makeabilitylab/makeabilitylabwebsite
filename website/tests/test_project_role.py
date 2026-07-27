"""Tests for ProjectRole model helpers.

Covers ``ProjectRole.position_during_role`` (#1426): the rule that decides which
Position a person held when they started a project role. The public REST API
serializes it (``position_title`` / ``position_school`` /
``position_school_abbreviated``), but the rules are exercised here, directly
against the model, so a failure points at the resolution logic rather than at
the API contract. The wire contract is pinned in test_api.py.
"""

from datetime import date

from website.models import Position, ProjectRole
from website.models.position import Title
from website.tests.base import DatabaseTestCase


class PositionDuringRoleTests(DatabaseTestCase):
    def setUp(self):
        self.project = self.make_project(name="Project Sidewalk",
                                         short_name="projectsidewalk")
        self.person = self.make_person(first_name="Ada", last_name="Holder")

    def _position(self, title, start, end=None, school="University of Maryland"):
        return Position.objects.create(
            person=self.person, title=title, school=school,
            start_date=start, end_date=end,
        )

    def _role(self, start, end=None):
        return ProjectRole.objects.create(
            person=self.person, project=self.project,
            start_date=start, end_date=end,
        )

    def test_returns_position_containing_role_start(self):
        """The headline case: what they were when they joined, not what they are
        now. An undergrad who later did an MS reads 'Undergrad' on a 2016 stint.
        """
        ugrad = self._position(Title.UGRAD, date(2015, 1, 1), date(2017, 5, 31))
        self._position(Title.MS_STUDENT, date(2017, 6, 1), date(2019, 6, 1),
                       school="University of Washington")
        role = self._role(date(2016, 1, 1), date(2018, 1, 1))
        self.assertEqual(role.position_during_role, ugrad)

    def test_overlapping_positions_pick_the_latest_to_start(self):
        """Positions can overlap (a title change recorded as a new row without
        closing the old one). The most recently started one wins -- it's the
        better description of the person at that moment."""
        self._position(Title.UGRAD, date(2015, 1, 1), date(2019, 1, 1))
        ms = self._position(Title.MS_STUDENT, date(2017, 1, 1), date(2019, 1, 1))
        role = self._role(date(2018, 1, 1))
        self.assertEqual(role.position_during_role, ms)

    def test_open_ended_position_contains_later_role(self):
        """A position with no end date contains everything after its start."""
        phd = self._position(Title.PHD_STUDENT, date(2015, 1, 1), None)
        role = self._role(date(2023, 6, 1))
        self.assertEqual(role.position_during_role, phd)

    def test_falls_back_to_prior_position_when_role_starts_in_a_gap(self):
        """A role starting between two positions reports the most recent one
        that had already started -- not the nearest in time."""
        ugrad = self._position(Title.UGRAD, date(2014, 1, 1), date(2015, 1, 1))
        self._position(Title.PHD_STUDENT, date(2019, 1, 1), None)
        role = self._role(date(2017, 1, 1))
        self.assertEqual(role.position_during_role, ugrad)

    def test_falls_back_to_earliest_when_role_predates_every_position(self):
        """Data drift, common in older imported roles: report the earliest
        position rather than nothing."""
        phd = self._position(Title.PHD_STUDENT, date(2020, 1, 1), None)
        self._position(Title.POST_DOC, date(2025, 1, 1), None)
        role = self._role(date(2018, 1, 1))
        self.assertEqual(role.position_during_role, phd)

    def test_none_when_person_has_no_positions(self):
        """Real case: external collaborators hold ProjectRoles but no Position."""
        role = self._role(date(2018, 1, 1))
        self.assertIsNone(role.position_during_role)

    def test_same_start_date_ties_break_deterministically(self):
        """Two positions starting the same day (concurrent Member/Collaborator
        rows, or a duplicate entry) must not let DB row order decide the answer:
        position_set has no Meta.ordering, so the tie breaks on pk."""
        self._position(Title.UGRAD, date(2015, 1, 1), None)
        later_row = self._position(Title.SOFTWARE_DEVELOPER, date(2015, 1, 1), None)
        role = self._role(date(2016, 1, 1))
        self.assertEqual(role.position_during_role, later_row)

    def test_resolves_without_extra_queries_when_prefetched(self):
        """The API relies on this riding prefetch_related('person__position_set')
        -- see test_api's N+1 guard. Pinned here too since it's a property of the
        model helper (it filters in Python), not of the view."""
        self._position(Title.UGRAD, date(2015, 1, 1), None)
        self._role(date(2016, 1, 1))
        role = (ProjectRole.objects
                .prefetch_related("person__position_set")
                .get(project=self.project))
        with self.assertNumQueries(0):
            self.assertIsNotNone(role.position_during_role)
