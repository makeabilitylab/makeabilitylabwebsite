"""
Tests for the ``seed_sidewalk_participants`` management command.

The command runs on every container start (docker-entrypoint.sh), so the
properties that matter most are that it is idempotent and that it never
clobbers records an editor has since tuned in /admin. It also has to actually
surface people through the public API, since that endpoint is what Project
Sidewalk consumes as its source of truth.
"""

from datetime import date
from io import StringIO

from django.core.management import call_command

from website.models import Person, Position, Project, ProjectRole
from website.models.position import Role, Title
from website.management.commands.seed_sidewalk_participants import (
    PARTICIPANTS,
    SIDEWALK_SLUG,
    UNRESOLVED,
)
from website.tests.base import DatabaseTestCase


def _seedable():
    """Entries the command will actually act on (all titles confirmed)."""
    return [e for e in PARTICIPANTS
            if not any(p['title'] is UNRESOLVED for p in e['positions'])]


class SeedSidewalkParticipantsTests(DatabaseTestCase):

    def setUp(self):
        self.project = Project.objects.create(
            name='Project Sidewalk', short_name=SIDEWALK_SLUG, is_visible=True)

    def _run(self, **kwargs):
        out = StringIO()
        call_command('seed_sidewalk_participants', stdout=out, **kwargs)
        return out.getvalue()

    def test_creates_new_people_with_collaborator_positions(self):
        """UIC participants get a Person, a Collaborator Position, and a role."""
        self._run()

        juan = Person.objects.get(first_name='Juan', last_name='Rosendo')
        position = Position.objects.get(person=juan)
        self.assertEqual(position.role, Role.COLLABORATOR)
        self.assertEqual(position.title, Title.UGRAD)
        self.assertEqual(position.school, 'University of Illinois Chicago')
        self.assertTrue(position.is_collaborator())

        role = ProjectRole.objects.get(person=juan, project=self.project)
        self.assertEqual(role.start_date, date(2022, 10, 1))
        self.assertEqual(role.end_date, date(2025, 9, 30))
        self.assertIn('auditing', role.role)

    def test_link_only_entries_do_not_create_a_position(self):
        """
        People who already have a member page only need a ProjectRole. The
        command must not invent a second Position for them.
        """
        heer = self.make_person(first_name='Jeffrey', last_name='Heer')
        Position.objects.create(
            person=heer, title=Title.FULL_PROF, role=Role.COLLABORATOR,
            start_date=date(2015, 1, 1))

        self._run()

        self.assertEqual(Position.objects.filter(person=heer).count(), 1)
        self.assertEqual(
            ProjectRole.objects.filter(person=heer, project=self.project).count(), 1)

    def test_link_only_entry_skipped_when_person_missing(self):
        """
        A link-only entry names someone expected to already exist. If they
        don't, the command must skip rather than create a Person with no
        Position (which would strand them off the People page).
        """
        self._run()
        self.assertFalse(
            Person.objects.filter(first_name='Jeffrey', last_name='Heer').exists())

    def test_is_idempotent(self):
        """Running twice creates nothing the second time."""
        self._run()
        people = Person.objects.count()
        positions = Position.objects.count()
        roles = ProjectRole.objects.count()

        output = self._run()

        self.assertEqual(Person.objects.count(), people)
        self.assertEqual(Position.objects.count(), positions)
        self.assertEqual(ProjectRole.objects.count(), roles)
        self.assertIn('0 people, 0 positions, 0 project roles created', output)

    def test_does_not_overwrite_admin_edits(self):
        """
        An editor's corrections in /admin survive the next container start.
        This is the whole reason the command is create-only.
        """
        self._run()
        juan = Person.objects.get(first_name='Juan', last_name='Rosendo')

        position = Position.objects.get(person=juan)
        position.title = Title.MS_STUDENT
        position.department = 'Urban Planning and Policy'
        position.save()

        role = ProjectRole.objects.get(person=juan, project=self.project)
        role.role = 'Hand-written by an editor'
        role.end_date = date(2025, 6, 1)
        role.save()

        self._run()

        position.refresh_from_db()
        role.refresh_from_db()
        self.assertEqual(position.title, Title.MS_STUDENT)
        self.assertEqual(position.department, 'Urban Planning and Policy')
        self.assertEqual(role.role, 'Hand-written by an editor')
        self.assertEqual(role.end_date, date(2025, 6, 1))

    def test_unresolved_titles_are_held_back(self):
        """
        Any entry with an unconfirmed title must be skipped whole -- no
        half-created Person with no Position. Guards against someone "fixing"
        the sentinel by defaulting it to a guess.

        All titles are currently confirmed, so this asserts the *mechanism*
        rather than a specific person, and keeps working if a future NSF
        report adds someone whose title we don't know yet.
        """
        self._run()

        for entry in PARTICIPANTS:
            if not any(p['title'] is UNRESOLVED for p in entry['positions']):
                continue
            self.assertFalse(
                Person.objects.filter(
                    first_name__iexact=entry['first_name'],
                    last_name__iexact=entry['last_name']).exists(),
                f"{entry['first_name']} {entry['last_name']} should be held back")

    def test_title_change_mid_grant_creates_two_positions(self):
        """
        Lauren Frame was an undergrad through May 2024 and started UIC's
        Occupational Therapy Doctorate that August, so her span needs two
        Positions rather than one averaged-out title.
        """
        self._run()

        lauren = Person.objects.get(first_name='Lauren', last_name='Frame')
        positions = Position.objects.filter(person=lauren).order_by('start_date')

        self.assertEqual(positions.count(), 2)
        self.assertEqual(positions[0].title, Title.UGRAD)
        self.assertEqual(positions[0].end_date, date(2024, 5, 31))
        self.assertEqual(positions[1].title, Title.PHD_STUDENT)
        self.assertEqual(positions[1].start_date, date(2024, 8, 1))

        # One continuous Sidewalk role spanning both, not one per position.
        self.assertEqual(
            ProjectRole.objects.filter(person=lauren, project=self.project).count(), 1)

    def test_project_coordinator_title_is_usable(self):
        """
        KiAnna Mckee-Steen is a project coordinator, which needed a new Title.
        Pins that the choice exists and is ordered (position_admin.py sorts the
        dropdown by TITLE_ORDER_MAPPING and would KeyError on a missing entry).
        """
        self._run()

        kianna = Person.objects.get(first_name='KiAnna', last_name='Mckee-Steen')
        position = Position.objects.get(person=kianna)
        self.assertEqual(position.title, Title.PROJECT_COORDINATOR)
        self.assertIn(Title.PROJECT_COORDINATOR, Position.TITLE_ORDER_MAPPING)

    def test_every_title_is_in_the_order_mapping(self):
        """
        Guards the whole Title vocabulary, not just the one we added: an
        unmapped title crashes the Position admin's dropdown sort.
        """
        for title in Title:
            self.assertIn(title, Position.TITLE_ORDER_MAPPING, f"{title} unmapped")

    def test_dry_run_writes_nothing(self):
        output = self._run(dry_run=True)

        self.assertEqual(Person.objects.count(), 0)
        self.assertEqual(Position.objects.count(), 0)
        self.assertEqual(ProjectRole.objects.count(), 0)
        self.assertIn('dry run', output)

    def test_noop_when_sidewalk_project_missing(self):
        """On an environment without the Sidewalk project, exit cleanly."""
        Project.objects.filter(short_name__iexact=SIDEWALK_SLUG).delete()

        output = self._run()

        self.assertEqual(Person.objects.count(), 0)
        self.assertIn('not found', output)

    def test_seeded_people_appear_in_the_public_api(self):
        """
        End-to-end: the point of the backfill is that Sidewalk can see these
        people at /api/v1/projects/sidewalk/people/.
        """
        self._run()

        response = self.client.get(
            f'/api/v1/projects/{SIDEWALK_SLUG}/people/', {'page_size': 100})
        self.assertEqual(response.status_code, 200)

        names = {row['person']['name'] for row in response.json()['results']}
        self.assertIn('Juan Rosendo', names)
        self.assertIn('Adamaris Diaz', names)

        # Only the newly-created people; the link-only entries reference people
        # this test's DB doesn't have, so they're skipped by design.
        expected = sum(
            len(e['project_roles']) for e in _seedable() if e['positions'])
        self.assertEqual(response.json()['count'], expected)
