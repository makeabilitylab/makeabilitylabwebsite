"""
Tests for the repair_diverged_artifact_filenames command (#1390).

This recovers artifacts whose pdf_file/raw_file DB row points at a file that no
longer exists on disk because a buggy rename moved it but save() never committed
(the dotted-name extension bug). The content is safe on disk under a malformed,
extension-less name; the command finds that orphan by content type, renames it
to the correct standardized name, and repoints the DB.
"""

import os
import shutil
import tempfile

from django.core.management import call_command
from django.test import override_settings
from django.utils.text import get_valid_filename

from website.models import Artifact, Talk
from website.tests.base import DatabaseTestCase


class RepairDivergedArtifactFilenamesTests(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        # A disposable MEDIA_ROOT so model saves, the simulated rename, and the
        # command's repairs only ever touch files here — never the real media/,
        # and never leak files that would collide with a later test run.
        self.media_root = tempfile.mkdtemp(prefix="ml_media_test_")
        self.addCleanup(shutil.rmtree, self.media_root, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=self.media_root)
        override.enable()
        self.addCleanup(override.disable)

    def _simulate_divergence(self, talk, include_type_suffix=True,
                             name_suffix=""):
        """Reproduce the bug's end state for the pdf_file: move the real file to
        the extension-less standardized base (the orphan) and point the DB at a
        now-missing old name.

        ``include_type_suffix=False`` names the orphan under the pre-#1404
        scheme (no trailing "_Talk") — what an orphan left behind before that
        scheme change looks like. ``name_suffix`` appends a
        "-<timestamp>"-style uniqueness suffix to the orphan.
        """
        directory = os.path.dirname(talk.pdf_file.path)
        valid_base = get_valid_filename(Artifact.generate_filename(
            talk, include_type_suffix=include_type_suffix)) + name_suffix
        orphan_path = os.path.join(directory, valid_base)  # no extension
        os.rename(talk.pdf_file.path, orphan_path)
        # DB now references a file that isn't there.
        Talk.objects.filter(pk=talk.pk).update(
            pdf_file="talks/Old_Missing_Name_zABC123.pdf"
        )
        return valid_base, orphan_path

    def test_repairs_pdf_pointing_at_missing_file(self):
        alice = self.make_person(first_name="Alice", last_name="Smith")
        talk = self.make_talk(
            title="A Recoverable Talk", forum_name="CHI", year=2024,
            authors=[alice],
        )
        valid_base, orphan_path = self._simulate_divergence(talk)
        talk.refresh_from_db()
        self.assertFalse(talk.pdf_file.storage.exists(talk.pdf_file.name))
        self.assertTrue(os.path.exists(orphan_path))

        call_command("repair_diverged_artifact_filenames")

        talk.refresh_from_db()
        # DB now points at the standardized name WITH the .pdf extension restored,
        # and that file exists on disk; the extension-less orphan is gone.
        self.assertTrue(talk.pdf_file.name.endswith(".pdf"))
        self.assertEqual(
            os.path.basename(talk.pdf_file.name), valid_base + ".pdf"
        )
        self.assertTrue(talk.pdf_file.storage.exists(talk.pdf_file.name))
        self.assertFalse(os.path.exists(orphan_path))

    def test_repairs_orphan_left_under_the_pre_1404_base(self):
        """The #1390 bug predates the #1404 scheme change, so an orphan it left
        behind carries the OLD standardized base (no trailing "_Talk"). The
        command must still find it — and repairs it forward to the new-scheme
        name."""
        alice = self.make_person(first_name="Alice", last_name="Smith")
        talk = self.make_talk(
            title="A Recoverable Talk", forum_name="CHI", year=2024,
            authors=[alice],
        )
        _, orphan_path = self._simulate_divergence(
            talk, include_type_suffix=False)
        self.assertTrue(os.path.exists(orphan_path))

        call_command("repair_diverged_artifact_filenames")

        talk.refresh_from_db()
        new_base = get_valid_filename(Artifact.generate_filename(talk))
        self.assertEqual(
            os.path.basename(talk.pdf_file.name), new_base + ".pdf"
        )
        self.assertTrue(talk.pdf_file.storage.exists(talk.pdf_file.name))
        self.assertFalse(os.path.exists(orphan_path))

    def test_repairs_uniquified_orphan_under_the_pre_1404_base(self):
        """Same, for a pre-#1404 orphan whose name collided on disk and picked
        up the "-<timestamp>" uniqueness suffix (ensure_filename_is_unique)."""
        alice = self.make_person(first_name="Alice", last_name="Smith")
        talk = self.make_talk(
            title="A Recoverable Talk", forum_name="CHI", year=2024,
            authors=[alice],
        )
        _, orphan_path = self._simulate_divergence(
            talk, include_type_suffix=False, name_suffix="-1782399772.42")

        call_command("repair_diverged_artifact_filenames")

        talk.refresh_from_db()
        new_base = get_valid_filename(Artifact.generate_filename(talk))
        self.assertEqual(
            os.path.basename(talk.pdf_file.name), new_base + ".pdf"
        )
        self.assertTrue(talk.pdf_file.storage.exists(talk.pdf_file.name))
        self.assertFalse(os.path.exists(orphan_path))

    def test_dry_run_changes_nothing(self):
        alice = self.make_person(first_name="Alice", last_name="Smith")
        talk = self.make_talk(
            title="A Recoverable Talk", forum_name="CHI", year=2024,
            authors=[alice],
        )
        _, orphan_path = self._simulate_divergence(talk)

        call_command("repair_diverged_artifact_filenames", "--dry-run")

        talk.refresh_from_db()
        # Still diverged: orphan untouched, DB still points at the missing name.
        self.assertTrue(os.path.exists(orphan_path))
        self.assertEqual(
            os.path.basename(talk.pdf_file.name), "Old_Missing_Name_zABC123.pdf"
        )

    def test_healthy_artifact_is_untouched(self):
        alice = self.make_person(first_name="Alice", last_name="Smith")
        talk = self.make_talk(
            title="A Healthy Talk", forum_name="CHI", year=2024, authors=[alice]
        )
        name_before = talk.pdf_file.name
        self.assertTrue(talk.pdf_file.storage.exists(name_before))

        call_command("repair_diverged_artifact_filenames")

        talk.refresh_from_db()
        self.assertEqual(talk.pdf_file.name, name_before)
        self.assertTrue(talk.pdf_file.storage.exists(talk.pdf_file.name))
