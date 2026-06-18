"""
Regression tests for the ``delete_unused_files`` management command (#1278, item 5).

This command runs on **every container start** (see ``docker-entrypoint.sh``) and
**deletes files** off the media filesystem, so it is the single highest-risk
untested code path in the app: a logic slip here silently destroys real
publication / talk / poster PDFs and thumbnails in production. Until now it had
zero tests.

The command globs ``MEDIA_ROOT/{publications,talks,posters}`` (and their
``images/`` thumbnail subdirs) for files, removes from that set anything still
referenced by a DB row, and deletes whatever is left over. These tests pin the
three behaviors that matter:

1. **Orphans are deleted, referenced files are kept** — the core contract.
2. **easy-thumbnails ``_detail`` cache files are never touched** — they are
   owned by ``thumbnail_cleanup``; deleting them here would fight that command.
3. **It never crashes** on empty media dirs, zero DB rows, or a row whose
   ``FileField`` is empty (the null-``.path`` crash class called out in #1278).

Every test runs against a throwaway ``MEDIA_ROOT`` (a temp dir wired in via
``override_settings``) so no real media is ever at risk.
"""

import os
import shutil
import tempfile
from datetime import date

from django.core.management import call_command
from django.test import override_settings

from website.models import Publication
from website.tests.base import DatabaseTestCase


class DeleteUnusedFilesTests(DatabaseTestCase):
    """Exercise ``manage.py delete_unused_files`` against a temp MEDIA_ROOT."""

    def setUp(self):
        super().setUp()
        # A disposable media root so model saves and the command's deletions
        # only ever touch files under here, never the developer's real media/.
        self.media_root = tempfile.mkdtemp(prefix="ml_media_test_")
        self.addCleanup(shutil.rmtree, self.media_root, ignore_errors=True)

        override = override_settings(MEDIA_ROOT=self.media_root)
        override.enable()
        self.addCleanup(override.disable)

        # The command globs these dirs; create them so an empty run has
        # something to glob (mirrors a freshly-deployed container).
        for sub in ("publications/images", "talks/images", "posters/images"):
            os.makedirs(os.path.join(self.media_root, sub), exist_ok=True)

    def _write(self, relpath, content=b"unused"):
        """Write a stray file under MEDIA_ROOT and return its absolute path."""
        full = os.path.join(self.media_root, relpath)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as fh:
            fh.write(content)
        return full

    def test_orphan_publication_pdf_is_deleted_referenced_is_kept(self):
        """The whole point: drop the orphan, keep the file a DB row points at."""
        pub = self.make_publication(title="Kept Paper")
        referenced = pub.pdf_file.path
        self.assertTrue(os.path.exists(referenced))

        orphan = self._write("publications/orphan_abandoned.pdf", b"%PDF-1.4 orphan")

        call_command("delete_unused_files")

        self.assertFalse(os.path.exists(orphan), "unreferenced PDF should be deleted")
        self.assertTrue(os.path.exists(referenced), "referenced PDF must be kept")

    def test_easy_thumbnail_detail_files_are_preserved(self):
        """``_detail`` cache files belong to thumbnail_cleanup, not this command."""
        detail = self._write(
            "publications/images/Foo_CHI2022.jpg.300x0_q85_detail.jpg"
        )
        orphan_thumb = self._write("publications/images/orphan_thumb.jpg")

        call_command("delete_unused_files")

        self.assertTrue(
            os.path.exists(detail),
            "_detail easy-thumbnail file must be preserved",
        )
        self.assertFalse(
            os.path.exists(orphan_thumb),
            "unreferenced thumbnail should be deleted",
        )

    def test_orphan_talk_pdf_and_raw_files_are_deleted(self):
        """Talks: orphan .pdf/.pptx/.key go; the referenced talk PDF stays."""
        talk = self.make_talk(title="Kept Talk")
        referenced = talk.pdf_file.path

        orphan_pdf = self._write("talks/orphan_talk.pdf")
        orphan_pptx = self._write("talks/orphan_deck.pptx")
        orphan_key = self._write("talks/orphan_deck.key")

        call_command("delete_unused_files")

        self.assertTrue(os.path.exists(referenced), "referenced talk PDF must be kept")
        for stray in (orphan_pdf, orphan_pptx, orphan_key):
            self.assertFalse(os.path.exists(stray), f"{stray} should be deleted")

    def test_orphan_poster_files_are_deleted(self):
        """Posters: the raw set is .pptx/.key/.ai (note .ai, unlike talks)."""
        strays = [
            self._write("posters/orphan_poster.pdf"),
            self._write("posters/orphan_poster.ai"),
            self._write("posters/orphan_poster.key"),
            self._write("posters/orphan_poster.pptx"),
        ]

        call_command("delete_unused_files")

        for stray in strays:
            self.assertFalse(os.path.exists(stray), f"{stray} should be deleted")

    def test_delete_unused_files_helper_reports_count_and_bytes(self):
        """The low-level helper returns an accurate (count, total_bytes) tally."""
        from website.management.commands.delete_unused_files import Command

        f1 = self._write("publications/a.pdf", b"12345")  # 5 bytes
        f2 = self._write("publications/b.pdf", b"678")     # 3 bytes

        count, total_bytes = Command().delete_unused_files([f1, f2])

        self.assertEqual(count, 2)
        self.assertEqual(total_bytes, 8)
        self.assertFalse(os.path.exists(f1))
        self.assertFalse(os.path.exists(f2))

    def test_runs_cleanly_on_empty_media_and_no_db_rows(self):
        """Fresh deploy: empty media dirs, no DB rows -> no exception, no deletions."""
        call_command("delete_unused_files")  # reaching the next line == no crash

        for sub in ("publications", "talks", "posters"):
            self.assertTrue(os.path.isdir(os.path.join(self.media_root, sub)))

    def test_artifact_with_empty_pdf_field_does_not_crash(self):
        """A row whose pdf_file is empty must not crash the guarded .path access."""
        # Guards the null-FileField crash class flagged in #1278: the command's
        # `if pub.pdf_file:` check must short-circuit before touching `.path`.
        # Built via objects.create (a single, first-time save) so this test
        # isolates the *command's* guard; the separate Artifact.save() null-pdf
        # re-save crash is pinned in test_artifact.py.
        Publication.objects.create(title="No PDF", date=date(2024, 1, 1))
        self.assertFalse(bool(Publication.objects.get(title="No PDF").pdf_file))

        call_command("delete_unused_files")  # no AttributeError on empty .path
