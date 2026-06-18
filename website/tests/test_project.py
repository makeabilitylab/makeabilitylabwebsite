"""Tests for Project model methods (member count, time-worked annotation)."""

from datetime import date, timedelta
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from website.tests.base import DatabaseTestCase


# --- Project member count regression --------------------------------------


class ProjectCurrentMemberCountTests(SimpleTestCase):
    """
    Regression for Project.get_current_member_count: the method built a
    queryset but never returned it, so the admin column always displayed
    None. These tests pin both the return value and the filter semantics
    so a future caller can't quietly re-introduce the bug.
    """

    def _make_project_with_count(self, count):
        project = MagicMock()
        project.projectrole_set.filter.return_value\
            .values.return_value\
            .distinct.return_value\
            .count.return_value = count
        return project

    def test_returns_count_not_none(self):
        from website.models.project import Project
        project = self._make_project_with_count(7)
        self.assertEqual(Project.get_current_member_count(project), 7)

    def test_filters_on_open_ended_project_role(self):
        from website.models.project import Project
        project = self._make_project_with_count(0)
        Project.get_current_member_count(project)
        project.projectrole_set.filter.assert_called_with(end_date__isnull=True)


# --- Project.get_people time-worked annotation ----------------------------


class ProjectGetPeopleTimeWorkedTests(DatabaseTestCase):
    """
    Regression for the dead conditional in Project.get_people
    (models/project.py).

    The original time_worked expression was
        F('end_date') if F('end_date') is not None else timezone.now()
    but an F() object is never None, so the else branch was dead: ongoing
    roles (end_date=None) produced NULL durations and a NULL
    total_time_worked annotation. The fix coalesces end_date to today in
    the DB via Coalesce().
    """

    def _make_project(self, name="Test Project", short_name="testproj"):
        from website.models import Project
        return Project.objects.create(name=name, short_name=short_name)

    def _add_role(self, person, project, start, end=None):
        from website.models import ProjectRole
        return ProjectRole.objects.create(
            person=person, project=project, start_date=start, end_date=end
        )

    def test_ongoing_role_has_non_null_time_worked(self):
        project = self._make_project()
        person = self.make_person(first_name="Ada", last_name="Lovelace")
        self._add_role(
            person, project, date.today() - timedelta(days=100), end=None
        )

        result = list(project.get_people())  # default sorted_by="time_on_project"
        self.assertEqual(len(result), 1)
        time_worked = result[0].total_time_worked
        self.assertIsNotNone(time_worked)  # was None before the Coalesce fix
        self.assertGreaterEqual(time_worked, timedelta(days=99))

    def test_long_completed_role_outranks_short_ongoing_role(self):
        """
        Discriminating ordering check. With the bug, the ongoing role's
        NULL duration sorts NULLS-FIRST under Postgres DESC ordering, so
        the short ongoing role would wrongly rank first. With the fix the
        long completed role ranks first by actual duration.
        """
        project = self._make_project()
        long_done = self.make_person(first_name="Long", last_name="Veteran")
        short_ongoing = self.make_person(first_name="Short", last_name="Newcomer")
        self._add_role(
            long_done, project,
            date.today() - timedelta(days=400),
            end=date.today() - timedelta(days=35),
        )  # ~365 days
        self._add_role(
            short_ongoing, project,
            date.today() - timedelta(days=10), end=None,
        )  # ~10 days

        result = list(project.get_people())
        self.assertEqual(result[0], long_done)
        self.assertEqual(result[1], short_ongoing)


# --- get_pis / get_co_pis regression --------------------------------------


class ProjectGetPisCoPisTests(DatabaseTestCase):
    """
    Regression for Project.get_pis / get_co_pis (models/project.py).

    Both methods filtered on a nonexistent ``pi_member`` field (the real field
    is ``lead_project_role``), so any call raised FieldError. The fix filters
    on ``lead_project_role`` and returns a QuerySet of Person objects as the
    docstring promises (#1182).
    """

    def _add_role(self, person, project, lead_role):
        from website.models import ProjectRole
        return ProjectRole.objects.create(
            person=person, project=project,
            lead_project_role=lead_role, start_date=date.today(),
        )

    def test_get_pis_and_co_pis_return_correct_people(self):
        from website.models import Project
        from website.models.project_role import LeadProjectRoleTypes

        project = Project.objects.create(name="Lab Project", short_name="lab")
        pi = self.make_person(first_name="Jon", last_name="Froehlich")
        co_pi = self.make_person(first_name="Co", last_name="Investigator")
        student = self.make_person(first_name="Grad", last_name="Student")
        self._add_role(pi, project, LeadProjectRoleTypes.PI)
        self._add_role(co_pi, project, LeadProjectRoleTypes.CO_PI)
        self._add_role(student, project, LeadProjectRoleTypes.STUDENT_LEAD)

        self.assertEqual(list(project.get_pis()), [pi])
        self.assertEqual(list(project.get_co_pis()), [co_pi])

    def test_no_pi_returns_empty_queryset(self):
        from website.models import Project

        project = Project.objects.create(name="Empty Project", short_name="empty")
        self.assertEqual(list(project.get_pis()), [])
        self.assertEqual(list(project.get_co_pis()), [])

    def test_duplicate_pi_roles_deduplicated(self):
        """A person with two PI roles on one project appears once."""
        from website.models import Project
        from website.models.project_role import LeadProjectRoleTypes

        project = Project.objects.create(name="Dup Project", short_name="dup")
        pi = self.make_person(first_name="Repeat", last_name="Lead")
        self._add_role(pi, project, LeadProjectRoleTypes.PI)
        self._add_role(pi, project, LeadProjectRoleTypes.PI)

        self.assertEqual(list(project.get_pis()), [pi])
