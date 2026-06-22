"""
Tests for the propagate_publication_projects management command (#649):
copy a publication's projects onto its childless talk/video/poster.
"""

from django.core.management import call_command

from website.tests.base import DatabaseTestCase


class PropagatePublicationProjectsTests(DatabaseTestCase):
    def _run(self, **kwargs):
        call_command('propagate_publication_projects', **kwargs)

    def test_childless_talk_inherits_parent_projects(self):
        project = self.make_project(name="Inheriting Project")
        talk = self.make_talk(title="Conference talk", year=2024)
        pub = self.make_publication(title="The paper", year=2024, talk=talk)
        pub.projects.add(project)

        self._run()
        talk.refresh_from_db()
        self.assertEqual(set(talk.projects.all()), {project})

    def test_video_and_poster_children_also_inherit(self):
        project = self.make_project(name="Multi-child Project")
        video = self.make_video(title="Teaser", year=2024)
        pub = self.make_publication(title="Paper w/ video", year=2024, video=video)
        pub.projects.add(project)

        self._run()
        video.refresh_from_db()
        self.assertEqual(set(video.projects.all()), {project})

    def test_existing_child_links_are_left_untouched(self):
        """A child that already has a project must not be modified."""
        parent_project = self.make_project(name="Parent Project")
        other_project = self.make_project(name="Other Project")
        talk = self.make_talk(title="Already linked talk", year=2024)
        talk.projects.add(other_project)
        pub = self.make_publication(title="Paper", year=2024, talk=talk)
        pub.projects.add(parent_project)

        self._run()
        talk.refresh_from_db()
        # additive-only + skip-if-linked => unchanged, still just other_project
        self.assertEqual(set(talk.projects.all()), {other_project})

    def test_publication_without_projects_propagates_nothing(self):
        talk = self.make_talk(title="Orphan talk", year=2024)
        self.make_publication(title="Unlinked paper", year=2024, talk=talk)

        self._run()
        talk.refresh_from_db()
        self.assertEqual(talk.projects.count(), 0)

    def test_dry_run_writes_nothing(self):
        project = self.make_project(name="Dry Run Project")
        talk = self.make_talk(title="Talk", year=2024)
        pub = self.make_publication(title="Paper", year=2024, talk=talk)
        pub.projects.add(project)

        self._run(dry_run=True)
        talk.refresh_from_db()
        self.assertEqual(talk.projects.count(), 0)

    def test_idempotent(self):
        project = self.make_project(name="Idempotent Project")
        talk = self.make_talk(title="Talk", year=2024)
        pub = self.make_publication(title="Paper", year=2024, talk=talk)
        pub.projects.add(project)

        self._run()
        self._run()
        talk.refresh_from_db()
        self.assertEqual(set(talk.projects.all()), {project})
