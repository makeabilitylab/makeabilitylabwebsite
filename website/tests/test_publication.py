"""Tests for Publication model methods (BibTeX, forum name, author lookup)."""

from unittest.mock import MagicMock

from django.test import SimpleTestCase

from website.tests.base import DatabaseTestCase


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
