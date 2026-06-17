"""
Tests for the factory_boy fixtures (#1272).

These guard the factories themselves: that each builds a valid, saved instance
with the file fields populated (so the upload validators pass and Person skips
its Star Wars fallback), that the relationship graph composes, and that the
no-auto-authors contract the ``base.py`` helpers rely on holds.
"""

from website.models import Person, Project, ProjectRole, Publication
from website.tests.base import DatabaseTestCase
from website.tests.factories import (
    AwardFactory,
    NewsItemFactory,
    PersonFactory,
    PosterFactory,
    ProjectFactory,
    ProjectRoleFactory,
    PublicationFactory,
    TalkFactory,
    VideoFactory,
)


class FactoryTests(DatabaseTestCase):
    def test_each_factory_builds_a_saved_instance(self):
        """Every factory persists a row and fills the required fields."""
        for factory_cls in (
            PersonFactory,
            ProjectFactory,
            VideoFactory,
            PublicationFactory,
            TalkFactory,
            PosterFactory,
            NewsItemFactory,
            AwardFactory,
            ProjectRoleFactory,
        ):
            with self.subTest(factory=factory_cls.__name__):
                obj = factory_cls()
                self.assertIsNotNone(obj.pk)

    def test_person_image_fields_are_prepopulated(self):
        """
        PersonFactory sets image + easter_egg, so Person.save() never falls
        back to opening a random Star Wars file off disk.
        """
        person = PersonFactory()
        self.assertTrue(person.image)
        self.assertTrue(person.easter_egg)

    def test_factory_runs_through_url_name_collision_resolution(self):
        """
        Person.save() resolves url_name collisions by appending a counter, and
        the factory goes through save(), so two people with the *same* name
        still get distinct url_names. Force a collision rather than relying on
        Faker (whose values can't be counted on to repeat or to differ).
        """
        a = PersonFactory(first_name="Sam", last_name="Lee")
        b = PersonFactory(first_name="Sam", last_name="Lee")
        self.assertNotEqual(a.url_name, b.url_name)
        # A Faker-named batch also all persist (distinct names or not).
        PersonFactory.create_batch(5)
        self.assertEqual(Person.objects.count(), 7)

    def test_publication_has_no_authors_by_default(self):
        """
        The no-auto-authors contract: artifacts are authorless unless the
        caller passes authors=. The base.py make_* helpers depend on this.
        """
        pub = PublicationFactory()
        self.assertEqual(pub.authors.count(), 0)

    def test_authors_passed_explicitly_are_set_in_order(self):
        """Passing authors= populates the SortedManyToManyField."""
        a, b = PersonFactory(), PersonFactory()
        pub = PublicationFactory(authors=[a, b])
        self.assertEqual(list(pub.authors.all()), [a, b])

    def test_project_role_subfactories_compose_the_graph(self):
        """
        ProjectRoleFactory wires a Person to a Project through the role table
        without the caller building either side by hand.
        """
        role = ProjectRoleFactory()
        self.assertIsInstance(role.person, Person)
        self.assertIsInstance(role.project, Project)
        self.assertEqual(role.project.projectrole_set.count(), 1)

    def test_project_role_accepts_explicit_person_and_project(self):
        person = PersonFactory()
        project = ProjectFactory()
        role = ProjectRoleFactory(person=person, project=project)
        self.assertEqual(role.person, person)
        self.assertEqual(role.project, project)
        self.assertEqual(ProjectRole.objects.count(), 1)

    def test_award_recipients_are_linked(self):
        recipients = PersonFactory.create_batch(2)
        award = AwardFactory(recipients=recipients)
        self.assertEqual(award.recipients.count(), 2)

    def test_project_defaults_to_private(self):
        """ProjectFactory leaves Project.save()'s private-by-default in place."""
        self.assertFalse(ProjectFactory().is_visible)

    def test_make_helpers_delegate_to_factories(self):
        """
        The base.py helpers still honor their original keyword API — notably
        the ``year`` shorthand — now that they delegate to the factories.
        """
        pub = self.make_publication(title="Delegated", year=2021)
        self.assertEqual(pub.title, "Delegated")
        self.assertEqual(pub.date.year, 2021)
        self.assertIsInstance(pub, Publication)
