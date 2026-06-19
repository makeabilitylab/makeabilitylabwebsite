"""
Phase 2 of the admin changelist audit (#1346): N+1 query fixes on the Project
and Person changelists.

Two kinds of coverage:
  1. Correctness — the new get_queryset() annotations must return exactly what
     the original per-row model methods returned (get_publication_count,
     get_most_recent_artifact, get_contributor_count, the Person counts, etc.),
     and the rewritten prefetch-friendly Person model methods
     (get_latest_position / get_earliest_position / get_total_time_in_role /
     is_alumni_member) must be behavior-preserving.
  2. The actual regression — the changelist must issue a roughly constant number
     of queries regardless of how many rows are listed. We render the real admin
     ChangeList (filters + every column cell) for N rows, then for 2N rows, and
     assert the query count doesn't grow. Before the fix these pages were
     ~O(rows); a regression would make 2N cost more than N.
"""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.contrib.admin.templatetags.admin_list import items_for_result
from django.db import connection
from django.test import RequestFactory
from django.test.utils import CaptureQueriesContext

from website.models import (Person, Position, ProjectRole, Project, Banner)
from website.models.position import Role, Title
from website.admin.admin_site import ml_admin_site
from website.admin.person_admin import PersonAdmin
from website.admin.project_admin import ProjectAdmin
from website.tests.base import DatabaseTestCase


class _AdminPerfBase(DatabaseTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = get_user_model().objects.create_superuser(
            username="perfadmin", email="perf@example.com", password="x")

    def setUp(self):
        self.rf = RequestFactory()

    def _request(self, params=None):
        request = self.rf.get('/', params or {})
        request.user = self.superuser
        return request

    def _render_changelist(self, model_admin, params):
        """Render the real admin ChangeList (filters + every column cell) once."""
        request = self._request(params)
        cl = model_admin.get_changelist_instance(request)
        cl.get_results(request)
        for obj in cl.result_list:
            list(items_for_result(cl, obj, None))

    def _steady_state_query_count(self, model_admin, params):
        """Number of DB queries to render the changelist *in steady state*.

        We render once first to warm easy_thumbnails' per-image first-render
        cache (an image's thumbnail metadata is written on first generation, a
        pre-existing per-row cost that is out of scope for this N+1 fix and does
        zero DB work once cached), then measure the second render. What remains
        is the position/count machinery this phase optimized — which must be flat
        as rows grow.
        """
        self._render_changelist(model_admin, params)   # warm thumbnail cache
        with CaptureQueriesContext(connection) as ctx:
            self._render_changelist(model_admin, params)
        return len(ctx.captured_queries)


class PersonModelMethodTests(_AdminPerfBase):
    """The prefetch-friendly rewrites are behavior-preserving."""

    def _reload(self, person):
        # Re-fetch to clear cached_property values computed during creation.
        return Person.objects.get(pk=person.pk)

    def test_latest_and_earliest_position(self):
        person = self.make_person()
        old = Position.objects.create(person=person, start_date=date(2018, 1, 1),
                                      end_date=date(2019, 1, 1), role=Role.MEMBER,
                                      title=Title.MS_STUDENT)
        new = Position.objects.create(person=person, start_date=date(2021, 1, 1),
                                      end_date=None, role=Role.MEMBER,
                                      title=Title.PHD_STUDENT)
        person = self._reload(person)
        self.assertEqual(person.get_latest_position, new)
        self.assertEqual(person.get_earliest_position, old)

    def test_no_positions_returns_none(self):
        person = self._reload(self.make_person())
        self.assertIsNone(person.get_latest_position)
        self.assertIsNone(person.get_earliest_position)

    def test_total_time_in_role_and_alumni(self):
        person = self.make_person()
        Position.objects.create(person=person, start_date=date(2015, 1, 1),
                                end_date=date(2017, 1, 1), role=Role.MEMBER,
                                title=Title.MS_STUDENT)
        person = self._reload(person)
        self.assertTrue(person.is_alumni_member)
        self.assertEqual(person.get_total_time_as_member,
                         date(2017, 1, 1) - date(2015, 1, 1))

    def test_current_member_is_not_alumni(self):
        person = self.make_person()
        Position.objects.create(person=person, start_date=date(2022, 1, 1),
                                end_date=None, role=Role.MEMBER,
                                title=Title.PHD_STUDENT)
        person = self._reload(person)
        self.assertFalse(person.is_alumni_member)

    def test_total_time_in_role_none_when_role_never_held(self):
        person = self.make_person()
        Position.objects.create(person=person, start_date=date(2022, 1, 1),
                                end_date=None, role=Role.COLLABORATOR,
                                title=Title.UNKNOWN)
        person = self._reload(person)
        self.assertIsNone(person.get_total_time_as_member)


class PersonAdminAnnotationTests(_AdminPerfBase):
    """PersonAdmin count annotations equal the original model count methods."""

    def test_counts_match_model(self):
        person = self.make_person(first_name="Auth", last_name="Or")
        project = self.make_project(name="PA Proj", is_visible=True)
        ProjectRole.objects.create(person=person, project=project,
                                   start_date=date(2020, 1, 1))
        pub = self.make_publication(title="PA Pub", year=2021)
        pub.authors.add(person)
        talk = self.make_talk(title="PA Talk", year=2022)
        talk.authors.add(person)

        admin = PersonAdmin(Person, ml_admin_site)
        annotated = admin.get_queryset(self._request()).get(pk=person.pk)
        model_person = Person.objects.get(pk=person.pk)
        self.assertEqual(admin.project_count(annotated), model_person.get_project_count)
        self.assertEqual(admin.pub_count(annotated), model_person.get_pub_count)
        self.assertEqual(admin.talk_count(annotated), model_person.get_talk_count)

    def test_changelist_query_count_is_flat(self):
        admin = PersonAdmin(Person, ml_admin_site)

        def make_people(start, end):
            for i in range(start, end):
                p = self.make_person(first_name=f"P{i}", last_name=f"L{i}")
                Position.objects.create(person=p, start_date=date(2021, 1, 1),
                                        end_date=None, role=Role.MEMBER,
                                        title=Title.PHD_STUDENT)
                Position.objects.create(person=p, start_date=date(2018, 1, 1),
                                        end_date=date(2019, 1, 1), role=Role.MEMBER,
                                        title=Title.MS_STUDENT)
                proj = self.make_project(name=f"P{i} Proj", short_name=f"p{i}proj")
                ProjectRole.objects.create(person=p, project=proj,
                                           start_date=date(2021, 2, 1))

        params = {'position_role': 'all'}
        make_people(0, 4)
        n1 = self._steady_state_query_count(admin, params)
        make_people(4, 12)
        n2 = self._steady_state_query_count(admin, params)
        self.assertEqual(n1, n2,
                         f"People changelist N+1: {n1} -> {n2} queries as rows grew 4 -> 12")


class ProjectAdminAnnotationTests(_AdminPerfBase):
    """ProjectAdmin annotations equal the original per-row model methods."""

    def test_counts_and_most_recent_match_model(self):
        project = self.make_project(name="PX", is_visible=True)
        a = self.make_person(first_name="A", last_name="A")
        b = self.make_person(first_name="B", last_name="B")
        # a has a current and a past role (distinct-person counts must dedupe).
        ProjectRole.objects.create(person=a, project=project,
                                   start_date=date(2020, 1, 1), end_date=None)
        ProjectRole.objects.create(person=a, project=project,
                                   start_date=date(2019, 1, 1), end_date=date(2019, 6, 1))
        # b is a publication author but holds no role -> contributors = {a, b}.
        pub = self.make_publication(title="PX Pub", year=2021)
        pub.projects.add(project)
        pub.authors.add(b)
        talk = self.make_talk(title="PX Talk", year=2023)
        talk.projects.add(project)
        video = self.make_video(title="PX Video", year=2022)
        video.projects.add(project)
        Banner.objects.create(project=project, title="PX Banner")

        admin = ProjectAdmin(Project, ml_admin_site)
        ann = admin.get_queryset(self._request()).get(pk=project.pk)
        model_project = Project.objects.get(pk=project.pk)

        self.assertEqual(admin.pub_count(ann), model_project.get_publication_count())
        self.assertEqual(admin.talk_count(ann), model_project.get_talk_count())
        self.assertEqual(admin.video_count(ann), model_project.get_video_count())
        self.assertEqual(admin.banner_count(ann), model_project.get_banner_count())
        self.assertEqual(admin.people_count(ann), model_project.get_people_count())
        self.assertEqual(admin.current_member_count(ann),
                         model_project.get_current_member_count())
        self.assertEqual(admin.past_member_count(ann),
                         model_project.get_past_member_count())
        self.assertEqual(admin.contributor_count(ann),
                         model_project.get_contributor_count())
        self.assertEqual(admin.most_recent_artifact_date(ann),
                         model_project.get_most_recent_artifact_date())
        self.assertEqual(admin.most_recent_artifact_type(ann),
                         model_project.get_most_recent_artifact_type())
        # Sanity-check the actual values, not just agreement with the model.
        self.assertEqual(admin.contributor_count(ann), 2)
        self.assertEqual(admin.people_count(ann), 1)
        self.assertEqual(admin.most_recent_artifact_type(ann), 'Talk')

    def test_most_recent_artifact_single_type_and_empty(self):
        admin = ProjectAdmin(Project, ml_admin_site)

        solo = self.make_project(name="Solo", is_visible=True)
        pub = self.make_publication(title="Solo Pub", year=2020)
        pub.projects.add(solo)
        ann = admin.get_queryset(self._request()).get(pk=solo.pk)
        # Exercises Greatest() ignoring the NULL talk/video dates (Postgres).
        self.assertEqual(admin.most_recent_artifact_type(ann), 'Publication')
        self.assertEqual(admin.most_recent_artifact_date(ann), date(2020, 1, 1))

        empty = self.make_project(name="Empty", is_visible=True)
        ann_empty = admin.get_queryset(self._request()).get(pk=empty.pk)
        self.assertIsNone(admin.most_recent_artifact_type(ann_empty))
        self.assertIsNone(admin.most_recent_artifact_date(ann_empty))

    def test_changelist_query_count_is_flat(self):
        admin = ProjectAdmin(Project, ml_admin_site)

        def make_projects(start, end):
            for i in range(start, end):
                proj = self.make_project(name=f"Proj {i}", short_name=f"proj{i}",
                                         is_visible=True)
                person = self.make_person(first_name=f"PP{i}", last_name=f"LL{i}")
                ProjectRole.objects.create(person=person, project=proj,
                                           start_date=date(2021, 1, 1))
                Banner.objects.create(project=proj, title=f"B{i}")

        params = {'active_project_status': 'All'}
        make_projects(0, 4)
        n1 = self._steady_state_query_count(admin, params)
        make_projects(4, 12)
        n2 = self._steady_state_query_count(admin, params)
        self.assertEqual(n1, n2,
                         f"Project changelist N+1: {n1} -> {n2} queries as rows grew 4 -> 12")
