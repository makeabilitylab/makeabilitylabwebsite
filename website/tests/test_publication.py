"""Tests for Publication model methods (BibTeX, forum name, author lookup)."""

import io
import os
import tempfile
from unittest.mock import MagicMock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings

from website.tests.base import DatabaseTestCase


def _make_pdf_bytes(num_pages):
    """
    Build a minimal, valid in-memory PDF with `num_pages` blank pages, using
    pypdf's own writer. Guarantees a real PDF (so pypdf can re-read its page
    tree) with a known page count for assertions.
    """
    from pypdf import PdfWriter
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=612, height=792)  # US Letter
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


# --- BibTeX citation regression -------------------------------------------


class BibtexCitationTests(SimpleTestCase):
    """
    Regression tests for Publication.get_citation_as_bibtex.

    The method previously compared self.pub_venue_type with ``is`` against
    PubType.JOURNAL / PubType.ARTICLE. Because TextChoices values are strings
    loaded from the DB, the identity check was always False and every journal
    or article paper was emitted as @inproceedings{ instead of @article{.
    These tests pin the corrected behavior.
    """

    def _make_publication(self, pub_venue_type):
        """Mock Publication exposing only what get_citation_as_bibtex reads."""
        pub = MagicMock()
        pub.pub_venue_type = pub_venue_type
        pub.get_bibtex_id.return_value = "Doe2020FooCHI20,"
        pub.authors.all.return_value = []
        pub.title = "A Test Title"
        pub.book_title = "Proceedings of Test"
        pub.get_formatted_forum_name.return_value = "CHI"
        pub.date.year = 2020
        # Falsy values below match the "if self.X" guards in the method:
        # when falsy the optional bibtex fields are skipped without
        # exercising any further attribute access.
        pub.series = ""
        pub.isbn = ""
        pub.location = ""
        pub.page_num_start = None
        pub.page_num_end = None
        pub.num_pages = None
        pub.doi = ""
        pub.official_url = ""
        pub.acmid = ""
        pub.publisher = ""
        return pub

    def test_journal_uses_article_entry(self):
        from website.models.publication import Publication, PubType
        pub = self._make_publication(PubType.JOURNAL)
        bibtex = Publication.get_citation_as_bibtex(pub)
        self.assertTrue(
            bibtex.startswith("@article{"),
            msg=f"Expected JOURNAL to emit @article{{, got {bibtex[:60]!r}",
        )

    def test_article_uses_article_entry(self):
        from website.models.publication import Publication, PubType
        pub = self._make_publication(PubType.ARTICLE)
        bibtex = Publication.get_citation_as_bibtex(pub)
        self.assertTrue(
            bibtex.startswith("@article{"),
            msg=f"Expected ARTICLE to emit @article{{, got {bibtex[:60]!r}",
        )

    def test_conference_uses_inproceedings_entry(self):
        from website.models.publication import Publication, PubType
        pub = self._make_publication(PubType.CONFERENCE)
        bibtex = Publication.get_citation_as_bibtex(pub)
        self.assertTrue(
            bibtex.startswith("@inproceedings{"),
            msg=f"Expected CONFERENCE to emit @inproceedings{{, got {bibtex[:60]!r}",
        )


# --- Formatted forum name regression (#988) -------------------------------


class FormattedForumNameTests(SimpleTestCase):
    """
    Regression tests for Publication.get_formatted_forum_name (#988).

    The previous implementation bundled posters, demos, work-in-progress,
    and doctoral consortium papers all under one generic
    "Extended Abstract Proceedings of …" label, and didn't prefix workshop
    papers at all. Per the issue, each short-form category should get a
    specific label ("Poster Proceedings of …", "Demo Proceedings of …",
    "Workshop Proceedings of …", "Work-in-Progress Proceedings of …",
    "Doctoral Consortium Proceedings of …"). The bare `extended_abstract`
    boolean field remains the catch-all fallback when the venue type
    doesn't match a known short-form category.
    """

    def _make_publication(self, pub_venue_type, *, forum_name="CHI", year=2024,
                          extended_abstract=False):
        pub = MagicMock()
        pub.forum_name = forum_name
        pub.pub_venue_type = pub_venue_type
        pub.extended_abstract = extended_abstract
        pub.date.year = year
        return pub

    def test_conference_uses_proceedings_of(self):
        from website.models.publication import Publication, PubType
        pub = self._make_publication(PubType.CONFERENCE)
        self.assertEqual(
            Publication.get_formatted_forum_name(pub),
            "Proceedings of CHI 2024",
        )

    def test_poster_uses_poster_proceedings_of(self):
        from website.models.publication import Publication, PubType
        pub = self._make_publication(PubType.POSTER)
        self.assertEqual(
            Publication.get_formatted_forum_name(pub),
            "Poster Proceedings of CHI 2024",
        )

    def test_demo_uses_demo_proceedings_of(self):
        from website.models.publication import Publication, PubType
        pub = self._make_publication(PubType.DEMO)
        self.assertEqual(
            Publication.get_formatted_forum_name(pub),
            "Demo Proceedings of CHI 2024",
        )

    def test_workshop_uses_workshop_proceedings_of(self):
        from website.models.publication import Publication, PubType
        pub = self._make_publication(PubType.WORKSHOP)
        self.assertEqual(
            Publication.get_formatted_forum_name(pub),
            "Workshop Proceedings of CHI 2024",
        )

    def test_wip_uses_work_in_progress_proceedings_of(self):
        from website.models.publication import Publication, PubType
        pub = self._make_publication(PubType.WIP)
        self.assertEqual(
            Publication.get_formatted_forum_name(pub),
            "Work-in-Progress Proceedings of CHI 2024",
        )

    def test_doctoral_consortium_uses_doctoral_consortium_proceedings_of(self):
        from website.models.publication import Publication, PubType
        pub = self._make_publication(PubType.DOCTORAL_CONSORTIUM)
        self.assertEqual(
            Publication.get_formatted_forum_name(pub),
            "Doctoral Consortium Proceedings of CHI 2024",
        )

    def test_journal_has_no_prefix(self):
        """Journals are not 'Proceedings of …'; the forum name stands alone."""
        from website.models.publication import Publication, PubType
        pub = self._make_publication(PubType.JOURNAL, forum_name="TOCHI")
        self.assertEqual(
            Publication.get_formatted_forum_name(pub),
            "TOCHI 2024",
        )

    def test_article_has_no_prefix(self):
        from website.models.publication import Publication, PubType
        pub = self._make_publication(PubType.ARTICLE, forum_name="ArXiv")
        self.assertEqual(
            Publication.get_formatted_forum_name(pub),
            "ArXiv 2024",
        )

    def test_extended_abstract_flag_is_fallback(self):
        """
        The `extended_abstract` BooleanField stays as the catch-all when a
        pub doesn't fit a specific short-form category (e.g. a panel paper
        marked as a short submission).
        """
        from website.models.publication import Publication, PubType
        pub = self._make_publication(PubType.PANEL, extended_abstract=True)
        self.assertEqual(
            Publication.get_formatted_forum_name(pub),
            "Extended Abstract Proceedings of CHI 2024",
        )

    def test_empty_forum_name_returns_empty_string(self):
        from website.models.publication import Publication, PubType
        pub = self._make_publication(PubType.CONFERENCE, forum_name="")
        self.assertEqual(Publication.get_formatted_forum_name(pub), "")


# --- get_person regression (authorless publications) ----------------------


class PublicationGetPersonTests(DatabaseTestCase):
    """
    Regression for Publication.get_person (models/publication.py).

    The method indexed self.authors.all()[0], raising IndexError on an
    authorless publication (e.g. a PhD dissertation entered before its
    author is linked). This path is reached from views/people.py, which
    iterates dissertations and calls get_person() on each. The fix returns
    None via .first() so the caller can skip authorless rows.
    """

    def test_no_authors_returns_none(self):
        pub = self.make_publication(title="Authorless Paper")
        self.assertIsNone(pub.get_person())

    def test_returns_first_author_in_sorted_order(self):
        pub = self.make_publication(title="Authored Paper")
        first = self.make_person(first_name="First", last_name="Author")
        second = self.make_person(first_name="Second", last_name="Author")
        pub.authors.add(first, second)  # SortedManyToManyField preserves order
        self.assertEqual(pub.get_person(), first)


# --- get_pdf_page_count helper (#1298) ------------------------------------


class GetPdfPageCountTests(SimpleTestCase):
    """
    Unit tests for fileutils.get_pdf_page_count, which backs the auto-population
    of Publication.num_pages (#1298). The helper must return the page count for a
    valid PDF and None (never raise) for anything it can't read, so a bad upload
    never blocks saving a publication.
    """

    def _mock_field(self, name, path, exists=True):
        """Build a minimal FileField stand-in with the attrs the helper reads."""
        field = MagicMock()
        field.name = name
        field.path = path
        field.storage.exists.return_value = exists
        return field

    def test_returns_page_count_for_valid_pdf(self):
        from website.utils import fileutils
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(_make_pdf_bytes(7))
            tmp_path = tmp.name
        try:
            field = self._mock_field("paper.pdf", tmp_path)
            self.assertEqual(fileutils.get_pdf_page_count(field), 7)
        finally:
            os.unlink(tmp_path)

    def test_returns_none_for_non_pdf_extension(self):
        from website.utils import fileutils
        field = self._mock_field("notes.txt", "/tmp/notes.txt")
        self.assertIsNone(fileutils.get_pdf_page_count(field))

    def test_returns_none_when_file_missing_from_storage(self):
        from website.utils import fileutils
        field = self._mock_field("paper.pdf", "/tmp/does-not-exist.pdf", exists=False)
        self.assertIsNone(fileutils.get_pdf_page_count(field))

    def test_returns_none_for_corrupt_pdf(self):
        from website.utils import fileutils
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"%PDF-1.4 not actually a real pdf")
            tmp_path = tmp.name
        try:
            field = self._mock_field("paper.pdf", tmp_path)
            self.assertIsNone(fileutils.get_pdf_page_count(field))
        finally:
            os.unlink(tmp_path)

    def test_returns_none_for_empty_field(self):
        from website.utils import fileutils
        empty = MagicMock()
        empty.name = ""
        self.assertIsNone(fileutils.get_pdf_page_count(empty))


# --- num_pages auto-population on save (#1298) ----------------------------


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class NumPagesAutoFillTests(DatabaseTestCase):
    """
    Integration tests for Publication.save() auto-filling num_pages from the
    uploaded PDF (#1298). Uses a temp MEDIA_ROOT so the real PDFs/thumbnails the
    save path writes don't pollute the project's media/ directory.
    """

    def _pdf_upload(self, name, num_pages):
        return SimpleUploadedFile(
            name, _make_pdf_bytes(num_pages), content_type="application/pdf"
        )

    def test_num_pages_autofilled_from_pdf(self):
        pub = self.make_publication(
            title="Auto Pages", pdf_file=self._pdf_upload("auto.pdf", 5)
        )
        pub.refresh_from_db()
        self.assertEqual(pub.num_pages, 5)

    def test_manual_num_pages_is_preserved(self):
        """A page count the editor typed in must never be overwritten."""
        pub = self.make_publication(
            title="Manual Pages",
            num_pages=99,
            pdf_file=self._pdf_upload("manual.pdf", 5),
        )
        pub.refresh_from_db()
        self.assertEqual(pub.num_pages, 99)


# --- backfill_num_pages management command (#1298) ------------------------


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class BackfillNumPagesCommandTests(DatabaseTestCase):
    """
    Tests for the backfill_num_pages management command, which populates
    num_pages for legacy publications that have a PDF but no page count (#1298).
    """

    def _pdf_upload(self, name, num_pages):
        return SimpleUploadedFile(
            name, _make_pdf_bytes(num_pages), content_type="application/pdf"
        )

    def _make_legacy_pub(self, title, num_pages_in_pdf):
        """
        Create a publication and then null out num_pages directly in the DB to
        simulate a legacy row (save() auto-fills it, so we can't create one with
        an empty count through the normal path).
        """
        from website.models import Publication
        pub = self.make_publication(
            title=title, pdf_file=self._pdf_upload(f"{title}.pdf", num_pages_in_pdf)
        )
        Publication.objects.filter(pk=pub.pk).update(num_pages=None)
        return pub

    def test_backfills_missing_page_count(self):
        from django.core.management import call_command
        pub = self._make_legacy_pub("Legacy", 8)
        call_command("backfill_num_pages")
        pub.refresh_from_db()
        self.assertEqual(pub.num_pages, 8)

    def test_dry_run_makes_no_changes(self):
        from django.core.management import call_command
        pub = self._make_legacy_pub("DryRun", 8)
        call_command("backfill_num_pages", "--dry-run")
        pub.refresh_from_db()
        self.assertIsNone(pub.num_pages)

    def test_existing_count_is_not_overwritten(self):
        """Publications that already have a count are left untouched."""
        from django.core.management import call_command
        pub = self.make_publication(
            title="HasCount", num_pages=42, pdf_file=self._pdf_upload("hc.pdf", 8)
        )
        call_command("backfill_num_pages")
        pub.refresh_from_db()
        self.assertEqual(pub.num_pages, 42)
