"""
Regression tests for the "Artifacts not linked to a project" data-health check
(website/admin/data_health/checks/unlinked_artifacts.py, issue #649).
"""

from datetime import timedelta

from django.conf import settings

from website.admin.data_health.checks.unlinked_artifacts import (
    UnlinkedArtifactsCheck,
)
from website.tests.base import DatabaseTestCase


class UnlinkedArtifactsCheckTests(DatabaseTestCase):
    def setUp(self):
        self.check = UnlinkedArtifactsCheck()

    def _rows_by_type_id(self):
        return {(r['type'], r['id']): r for r in self.check.get_rows()}

    def test_unlinked_artifact_is_flagged(self):
        pub = self.make_publication(title="Orphan paper", year=2024)
        rows = self._rows_by_type_id()
        self.assertIn(('Publication', pub.pk), rows)

    def test_linked_artifact_is_not_flagged(self):
        pub = self.make_publication(title="Linked paper", year=2024)
        pub.projects.add(self.make_project(name="Some Project"))
        rows = self._rows_by_type_id()
        self.assertNotIn(('Publication', pub.pk), rows)

    def test_pre_lab_artifact_is_excluded(self):
        """Pre-Makeability-Lab work (grad school) shouldn't be flagged."""
        formed = settings.DATE_MAKEABILITYLAB_FORMED
        old = self.make_publication(
            title="Grad-school paper", date=formed - timedelta(days=1)
        )
        recent = self.make_publication(title="Lab paper", date=formed)
        rows = self._rows_by_type_id()
        self.assertNotIn(('Publication', old.pk), rows)
        self.assertIn(('Publication', recent.pk), rows)

    def test_child_of_linked_publication_gets_inherit_note(self):
        """A talk whose parent publication is linked should carry the
        propagation hint so it's an easy win."""
        talk = self.make_talk(title="Conference talk", year=2024)
        pub = self.make_publication(title="Talk's paper", year=2024, talk=talk)
        pub.projects.add(self.make_project(name="Parent Project"))

        row = self._rows_by_type_id()[('Talk', talk.pk)]
        self.assertIn('inherit', row['note'])

    def test_orphan_child_has_no_inherit_note(self):
        talk = self.make_talk(title="Standalone talk", year=2024)
        row = self._rows_by_type_id()[('Talk', talk.pk)]
        self.assertEqual(row['note'], '')

    def test_row_link_points_to_admin_change_page(self):
        pub = self.make_publication(title="Linkable paper", year=2024)
        row = self._rows_by_type_id()[('Publication', pub.pk)]
        label, url = self.check.row_link(row)
        self.assertIn(str(pub.pk), url)
        self.assertIn('publication', url)
