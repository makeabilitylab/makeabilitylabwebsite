"""
Tests for the website app.

Currently covers website.utils.bio_utils.auto_generate_bio. Tests use mocks
rather than real Person/Position records so they don't have to navigate
Person.save() side-effects (random image assignment, file I/O); the unit
under test is pure presentation logic.
"""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from website.utils.bio_utils import (
    _join_with_oxford_comma,
    auto_generate_bio,
    humanize_duration,
)


# --- Mock fixtures ---------------------------------------------------------


class FakeQuerySet:
    """Minimal stand-in for a Django QuerySet with the methods auto-bio uses."""

    def __init__(self, items):
        self._items = list(items)

    def count(self):
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    def __getitem__(self, key):
        return self._items[key]


def _make_person(
    *,
    first_name="Jon",
    last_name="Doe",
    url_name="jondoe",
    has_started=True,
    is_current_member=False,
    is_alumni_member=False,
    is_current_collaborator=False,
    is_past_collaborator=False,
    is_active=False,
    current_title="PhD Student",
    latest_position=None,
    publications=0,
    projects=None,
    mentors=None,
    mentees=None,
    total_time_as_member=None,
):
    """Build a mock Person exposing only the attributes auto_generate_bio reads."""
    # If the caller indicates the person has started, default to a non-None
    # latest_position so the "no positions at all" early-return doesn't
    # short-circuit the role-branch tests. Callers exercising the no-position
    # case pass has_started=False and leave latest_position as None.
    if latest_position is None and has_started:
        latest_position = _make_position(
            start_date=date(2020, 1, 1), title=current_title
        )

    person = MagicMock(name=f"Person({first_name} {last_name})")
    person.first_name = first_name
    person.last_name = last_name
    person.get_full_name.return_value = f"{first_name} {last_name}"
    person.get_url_name.return_value = url_name
    person.has_started = has_started
    person.is_current_member = is_current_member
    person.is_alumni_member = is_alumni_member
    person.is_current_collaborator = is_current_collaborator
    person.is_past_collaborator = is_past_collaborator
    person.is_active = is_active
    person.get_current_title = current_title
    person.get_latest_position = latest_position
    person.get_total_time_as_member = total_time_as_member
    person.get_projects = projects or []

    publication_set = MagicMock()
    publication_set.exists.return_value = publications > 0
    publication_set.count.return_value = publications
    person.publication_set = publication_set

    person.get_grad_mentors.return_value = FakeQuerySet(mentors or [])
    person.get_mentees.return_value = FakeQuerySet(mentees or [])
    return person


def _make_link_person(first_name, last_name, url_name):
    p = MagicMock()
    p.get_full_name.return_value = f"{first_name} {last_name}"
    p.get_url_name.return_value = url_name
    return p


def _make_project(name, short_name):
    p = MagicMock()
    p.name = name
    p.short_name = short_name
    return p


def _make_position(start_date=None, end_date=None, title="PhD Student"):
    pos = MagicMock()
    pos.start_date = start_date
    pos.end_date = end_date
    pos.title = title
    return pos


# --- Role-sentence reachability matrix -------------------------------------


class RoleSentenceTests(SimpleTestCase):
    """One test per branch of _role_sentence."""

    def test_no_position_no_publication_returns_empty(self):
        """
        Regression for #1258: a Person with no Position records AND no
        publications must produce an empty bio, not "will be joining…".
        """
        person = _make_person(has_started=False, publications=0)
        self.assertEqual(auto_generate_bio(person), "")

    def test_no_position_with_publication_says_has_published(self):
        person = _make_person(has_started=False, publications=3)
        bio = auto_generate_bio(person)
        self.assertIn("Jon Doe has published with the Makeability Lab.", bio)
        # Contributions sentence follows.
        self.assertIn("3 publications", bio)

    def test_future_member_says_will_be_joining_with_pretty_date(self):
        future_pos = _make_position(start_date=date(2026, 9, 15))
        person = _make_person(has_started=False, latest_position=future_pos)
        bio = auto_generate_bio(person)
        self.assertEqual(
            bio,
            "Jon Doe will be joining the Makeability Lab on Sep 2026.",
        )

    def test_current_member_with_duration(self):
        person = _make_person(
            is_current_member=True,
            is_active=True,
            current_title="PhD Student",
            total_time_as_member=timedelta(days=int(365 * 3 + 180)),
        )
        bio = auto_generate_bio(person)
        self.assertIn(
            "Jon Doe is currently a PhD Student in the Makeability Lab.", bio
        )
        self.assertIn("Jon has been in the lab for", bio)
        self.assertIn("years.", bio)

    def test_current_member_without_duration_omits_duration_sentence(self):
        person = _make_person(
            is_current_member=True,
            is_active=True,
            current_title="PhD Student",
            total_time_as_member=None,
        )
        bio = auto_generate_bio(person)
        self.assertEqual(
            bio, "Jon Doe is currently a PhD Student in the Makeability Lab."
        )

    def test_current_member_ms_uses_an_article(self):
        person = _make_person(
            is_current_member=True,
            is_active=True,
            current_title="MS Student",
            total_time_as_member=None,
        )
        bio = auto_generate_bio(person)
        self.assertIn("is currently an MS Student", bio)

    @patch("website.utils.bio_utils._get_earliest_member_position")
    @patch("website.utils.bio_utils._get_latest_member_position")
    def test_alumni_member_branch(self, mock_latest, mock_earliest):
        pos = _make_position(
            start_date=date(2018, 9, 1),
            end_date=date(2024, 3, 15),
            title="PhD Student",
        )
        mock_latest.return_value = pos
        mock_earliest.return_value = pos
        person = _make_person(
            is_alumni_member=True,
            current_title="PhD Student",
            total_time_as_member=timedelta(days=int(365 * 5.5)),
        )
        bio = auto_generate_bio(person)
        self.assertIn("Jon Doe was a PhD Student in the Makeability Lab", bio)
        self.assertIn("(Sep 2018 to Mar 2024).", bio)
        # Duration appears between the title and the date range.
        self.assertIn("years (Sep 2018 to Mar 2024).", bio)

    @patch("website.utils.bio_utils._get_earliest_member_position")
    @patch("website.utils.bio_utils._get_latest_member_position")
    def test_alumni_member_now_collaborator_gets_two_sentences(
        self, mock_latest, mock_earliest
    ):
        """
        Pre-fix bug: a former member who later became a current collaborator
        was described as "was a Collaborator … (… to present)". Now the
        first sentence anchors on the latest MEMBER position, and the
        current collaborator status is a separate trailing sentence.
        """
        pos = _make_position(
            start_date=date(2018, 9, 1),
            end_date=date(2024, 3, 15),
            title="PhD Student",
        )
        mock_latest.return_value = pos
        mock_earliest.return_value = pos
        person = _make_person(
            is_alumni_member=True,
            is_current_collaborator=True,
            current_title="Collaborator",
            total_time_as_member=timedelta(days=int(365 * 5.5)),
        )
        bio = auto_generate_bio(person)
        self.assertIn(
            "Jon Doe was a PhD Student in the Makeability Lab", bio
        )
        self.assertIn("(Sep 2018 to Mar 2024).", bio)
        self.assertIn(
            "Jon is currently a collaborator with the Makeability Lab.", bio
        )
        # The first sentence must NOT say "Collaborator" (the title attribute
        # of get_latest_position would say that — bug we're guarding against).
        self.assertNotIn("was a Collaborator", bio)
        self.assertNotIn("to present", bio)

    def test_current_collaborator(self):
        person = _make_person(
            is_current_collaborator=True, is_active=True
        )
        bio = auto_generate_bio(person)
        self.assertEqual(
            bio, "Jon Doe is a collaborator with the Makeability Lab."
        )

    def test_past_collaborator(self):
        person = _make_person(is_past_collaborator=True)
        bio = auto_generate_bio(person)
        self.assertEqual(
            bio, "Jon Doe was a collaborator with the Makeability Lab."
        )


# --- Contributions sentence ------------------------------------------------


class ContributionsSentenceTests(SimpleTestCase):
    """Shape of the projects/publications sentence."""

    def test_pubs_only_singular(self):
        person = _make_person(has_started=False, publications=1)
        bio = auto_generate_bio(person)
        self.assertIn("They contributed to 1 publication.", bio)

    def test_pubs_only_plural(self):
        person = _make_person(has_started=False, publications=5)
        bio = auto_generate_bio(person)
        self.assertIn("They contributed to 5 publications.", bio)

    def test_one_project_no_pubs(self):
        proj = _make_project("Sound Watch", "soundwatch")
        person = _make_person(
            is_current_member=True,
            is_active=True,
            current_title="PhD Student",
            projects=[proj],
        )
        bio = auto_generate_bio(person)
        self.assertIn("They contributed to a project called <a href=", bio)
        self.assertIn(">Sound Watch</a>.", bio)

    def test_two_projects_uses_and(self):
        projs = [
            _make_project("Alpha", "alpha"),
            _make_project("Beta", "beta"),
        ]
        person = _make_person(
            is_current_member=True,
            is_active=True,
            current_title="PhD Student",
            projects=projs,
        )
        bio = auto_generate_bio(person)
        self.assertIn("They contributed to 2 projects:", bio)
        self.assertIn(">Alpha</a> and <a", bio)

    def test_three_projects_uses_oxford_comma(self):
        projs = [
            _make_project("Alpha", "alpha"),
            _make_project("Beta", "beta"),
            _make_project("Gamma", "gamma"),
        ]
        person = _make_person(
            is_current_member=True,
            is_active=True,
            current_title="PhD Student",
            projects=projs,
        )
        bio = auto_generate_bio(person)
        self.assertIn("3 projects:", bio)
        # Oxford comma + "and" before the last item.
        self.assertIn(">Beta</a>, and <a", bio)

    def test_four_or_more_projects_uses_including(self):
        projs = [_make_project(f"P{c}", f"p{c}") for c in "abcdef"]
        person = _make_person(
            is_current_member=True,
            is_active=True,
            current_title="PhD Student",
            projects=projs,
        )
        bio = auto_generate_bio(person)
        self.assertIn(f"{len(projs)} projects, including", bio)

    def test_project_and_pubs_joined_with_as_well_as(self):
        proj = _make_project("Alpha", "alpha")
        person = _make_person(
            is_current_member=True,
            is_active=True,
            current_title="PhD Student",
            projects=[proj],
            publications=4,
        )
        bio = auto_generate_bio(person)
        self.assertIn("as well as 4 publications.", bio)


# --- Mentor / mentee sentences --------------------------------------------


class MentorMenteeSentenceTests(SimpleTestCase):
    def test_no_mentors_no_mentees_no_sentence(self):
        person = _make_person(
            is_current_member=True, is_active=True, current_title="PhD Student"
        )
        bio = auto_generate_bio(person)
        self.assertNotIn("mentored", bio)

    def test_mentor_sentence_active_uses_is(self):
        m = _make_link_person("Alice", "Smith", "alicesmith")
        person = _make_person(
            is_current_member=True,
            is_active=True,
            current_title="PhD Student",
            mentors=[m],
        )
        bio = auto_generate_bio(person)
        self.assertIn("Jon is mentored by", bio)
        self.assertIn(">Alice Smith</a>.", bio)

    @patch("website.utils.bio_utils._get_earliest_member_position")
    @patch("website.utils.bio_utils._get_latest_member_position")
    def test_mentor_sentence_inactive_uses_was(self, mock_latest, mock_earliest):
        pos = _make_position(
            start_date=date(2018, 9, 1),
            end_date=date(2024, 3, 15),
            title="PhD Student",
        )
        mock_latest.return_value = pos
        mock_earliest.return_value = pos
        m = _make_link_person("Alice", "Smith", "alicesmith")
        person = _make_person(
            is_alumni_member=True,
            is_active=False,
            current_title="PhD Student",
            mentors=[m],
        )
        bio = auto_generate_bio(person)
        self.assertIn("Jon was mentored by", bio)

    def test_mentor_sentence_multiple_uses_oxford_comma(self):
        mentors = [
            _make_link_person("Alice", "Smith", "alicesmith"),
            _make_link_person("Bob", "Jones", "bobjones"),
            _make_link_person("Carol", "Lee", "carollee"),
        ]
        person = _make_person(
            is_current_member=True,
            is_active=True,
            current_title="PhD Student",
            mentors=mentors,
        )
        bio = auto_generate_bio(person)
        self.assertIn("Jon is mentored by", bio)
        self.assertIn(", and ", bio)

    def test_mentee_member_uses_during_their_time_intro(self):
        person = _make_person(
            is_current_member=True,
            is_active=True,
            current_title="PhD Student",
            mentees=[_make_link_person("Mia", "X", "miax")],
        )
        bio = auto_generate_bio(person)
        self.assertIn(
            "During their time in the lab, Jon mentored 1 Makeability Lab student",
            bio,
        )

    def test_mentee_collaborator_uses_has_mentored_intro(self):
        person = _make_person(
            is_current_collaborator=True,
            is_active=True,
            mentees=[_make_link_person("Mia", "X", "miax")],
        )
        bio = auto_generate_bio(person)
        self.assertNotIn("During their time in the lab", bio)
        self.assertIn("Jon has mentored 1 Makeability Lab student", bio)

    def test_mentee_count_three_uses_colon(self):
        mentees = [
            _make_link_person("Mia", "X", "miax"),
            _make_link_person("Noah", "Y", "noahy"),
            _make_link_person("Olivia", "Z", "oliviaz"),
        ]
        person = _make_person(
            is_current_member=True,
            is_active=True,
            current_title="PhD Student",
            mentees=mentees,
        )
        bio = auto_generate_bio(person)
        self.assertIn("mentored 3 Makeability Lab students:", bio)

    def test_mentee_count_more_than_three_uses_including(self):
        mentees = [
            _make_link_person(f"M{i}", "X", f"m{i}x") for i in range(10)
        ]
        person = _make_person(
            is_current_member=True,
            is_active=True,
            current_title="PhD Student",
            mentees=mentees,
        )
        bio = auto_generate_bio(person)
        self.assertIn("mentored 10 Makeability Lab students, including", bio)


# --- HTML escaping ---------------------------------------------------------


class HtmlEscapingTests(SimpleTestCase):
    """Defensive: free-text spliced into anchor tags must be escaped."""

    def test_person_name_with_angle_brackets_is_escaped(self):
        person = _make_person(
            first_name="<script>",
            last_name="Doe",
            is_current_member=True,
            is_active=True,
            current_title="PhD Student",
        )
        bio = auto_generate_bio(person)
        self.assertNotIn("<script>", bio)
        self.assertIn("&lt;script&gt;", bio)

    def test_project_name_with_html_is_escaped(self):
        person = _make_person(
            is_current_member=True,
            is_active=True,
            current_title="PhD Student",
            projects=[_make_project("Bad <Project>", "badproject")],
        )
        bio = auto_generate_bio(person)
        self.assertNotIn("<Project>", bio)
        self.assertIn("Bad &lt;Project&gt;", bio)


# --- Helpers ---------------------------------------------------------------


class JoinWithOxfordCommaTests(SimpleTestCase):
    def test_empty(self):
        self.assertEqual(_join_with_oxford_comma([]), "")

    def test_one(self):
        self.assertEqual(_join_with_oxford_comma(["A"]), "A")

    def test_two(self):
        self.assertEqual(_join_with_oxford_comma(["A", "B"]), "A and B")

    def test_three_uses_oxford_comma(self):
        self.assertEqual(
            _join_with_oxford_comma(["A", "B", "C"]), "A, B, and C"
        )

    def test_four_uses_oxford_comma(self):
        self.assertEqual(
            _join_with_oxford_comma(["A", "B", "C", "D"]), "A, B, C, and D"
        )


class HumanizeDurationTests(SimpleTestCase):
    def test_under_a_month(self):
        self.assertEqual(
            humanize_duration(timedelta(days=10)), "less than a month"
        )

    def test_one_month(self):
        self.assertEqual(humanize_duration(timedelta(days=30)), "1 month")

    def test_six_months(self):
        self.assertEqual(humanize_duration(timedelta(days=180)), "6 months")

    def test_one_and_a_half_years(self):
        self.assertEqual(
            humanize_duration(timedelta(days=int(365 * 1.5))), "1.5 years"
        )

    def test_returns_years_string_for_long_durations(self):
        # Exact float value depends on 30-day-month approximation; we only
        # assert the format here.
        result = humanize_duration(timedelta(days=365 * 5))
        self.assertTrue(
            result.endswith(" years"),
            msg=f"Expected a years string, got {result!r}",
        )


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


# --- serve_pdf regression -------------------------------------------------


class ServePdfTests(SimpleTestCase):
    """
    Regression tests for website.views.serve_pdf.

    The previous implementation used
        Publication.objects.get(pdf_file__icontains=filename)
    which had two failure modes:

    1. Only ``ObjectDoesNotExist`` was caught. When a substring matched
       multiple publications' stored paths, ``MultipleObjectsReturned``
       was raised and propagated as a 500 — e.g. requesting "Speech"
       when both "Froehlich2010Speech.pdf" and
       "Froehlich2010Speechalytics.pdf" exist.
    2. ``__icontains`` is a substring match (SQL ``LIKE %x%``), so a
       probe for ".pdf" matched every PDF in the database. Combined with
       the fuzzy difflib fallback that redirects on miss, this enabled
       enumeration of stored filenames.

    The fix uses ``filter(pdf_file__iendswith=filename).first()`` for
    the exact branch: ``.first()`` can't raise ``MultipleObjectsReturned``,
    and ``__iendswith`` only matches paths ending in the requested name.
    The fuzzy difflib fallback is retained for academic-link integrity
    and is only invoked on actual miss.
    """

    def test_exact_match_returns_pdf_response(self):
        """Happy path: an exact filename match returns the PDF inline."""
        from website.views.serve_pdf import serve_pdf
        fake_pub = MagicMock()
        fake_pub.pdf_file.read.return_value = b"%PDF-1.4 fake"
        fake_pub.pdf_file.name = "publications/Froehlich2018Speech.pdf"
        with patch("website.views.serve_pdf.Publication") as MockPub:
            MockPub.objects.filter.return_value.first.return_value = fake_pub
            response = serve_pdf(MagicMock(), "Froehlich2018Speech.pdf")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_uses_iendswith_not_icontains(self):
        """
        Regression for the substring-probe enumeration bug. The exact
        branch must use ``__iendswith``; a request for ".pdf" must
        therefore miss (since no pub's path equals ".pdf") rather than
        matching every pub via substring.
        """
        from django.http import Http404
        from website.views.serve_pdf import serve_pdf
        with patch("website.views.serve_pdf.Publication") as MockPub, patch(
            "website.views.serve_pdf.get_closest_filename_from_database",
            return_value=None,
        ):
            MockPub.objects.filter.return_value.first.return_value = None
            with self.assertRaises(Http404):
                serve_pdf(MagicMock(), ".pdf")
            MockPub.objects.filter.assert_called_with(pdf_file__iendswith=".pdf")

    def test_no_exact_match_uses_fuzzy_redirect(self):
        """
        Stale-external-link preservation. When the exact branch misses,
        the difflib fallback should redirect to the closest filename it
        finds. This is the academic-link-integrity feature.
        """
        from website.views.serve_pdf import serve_pdf
        with patch("website.views.serve_pdf.Publication") as MockPub, patch(
            "website.views.serve_pdf.get_closest_filename_from_database",
            return_value="publications/Froehlich2018Updated.pdf",
        ):
            MockPub.objects.filter.return_value.first.return_value = None
            response = serve_pdf(MagicMock(), "Froehlich2018Old.pdf")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/media/publications/Froehlich2018Updated.pdf")

    def test_no_exact_no_fuzzy_returns_404(self):
        """If neither the exact branch nor the fuzzy fallback finds anything, 404."""
        from django.http import Http404
        from website.views.serve_pdf import serve_pdf
        with patch("website.views.serve_pdf.Publication") as MockPub, patch(
            "website.views.serve_pdf.get_closest_filename_from_database",
            return_value=None,
        ):
            MockPub.objects.filter.return_value.first.return_value = None
            with self.assertRaises(Http404):
                serve_pdf(MagicMock(), "NoSuchPaper.pdf")


# --- Artifact filename check regression -----------------------------------


class ArtifactFilenameUpdateCheckTests(SimpleTestCase):
    """
    Regression tests for Artifact.do_filenames_need_updating.

    The raw_file and thumbnail branches each compared against
    ``artifact.pdf_file.name`` (copy-pasted from the pdf_file branch)
    instead of ``artifact.raw_file.name`` / ``artifact.thumbnail.name``.
    The bug masked filename drift in those fields: when pdf_file matched
    but raw_file or thumbnail had a stale name, the function returned
    False instead of True. These tests pin the per-branch lookup.
    """

    def _patch_generate(self, value):
        return patch(
            "website.models.artifact.Artifact.generate_filename",
            return_value=value,
        )

    def test_all_matching_returns_false(self):
        from website.models.artifact import Artifact
        with self._patch_generate("Doe2020Title"):
            artifact = MagicMock()
            artifact.pdf_file = MagicMock()
            artifact.pdf_file.name = "publications/Doe2020Title.pdf"
            artifact.raw_file = MagicMock()
            artifact.raw_file.name = "publications/Doe2020Title.zip"
            artifact.thumbnail = MagicMock()
            artifact.thumbnail.name = "thumbnails/Doe2020Title.jpg"
            self.assertFalse(Artifact.do_filenames_need_updating(artifact))

    def test_raw_file_mismatch_when_pdf_file_matches(self):
        """
        Under the bug the raw_file branch looked at pdf_file.name (which
        matches) and returned False; the fix makes it look at
        raw_file.name and correctly report the mismatch.
        """
        from website.models.artifact import Artifact
        with self._patch_generate("Doe2020Title"):
            artifact = MagicMock()
            artifact.pdf_file = MagicMock()
            artifact.pdf_file.name = "publications/Doe2020Title.pdf"
            artifact.raw_file = MagicMock()
            artifact.raw_file.name = "publications/StaleName.zip"
            artifact.thumbnail = None
            self.assertTrue(Artifact.do_filenames_need_updating(artifact))

    def test_thumbnail_mismatch_when_pdf_file_matches(self):
        """Same shape as the raw_file regression, for the thumbnail branch."""
        from website.models.artifact import Artifact
        with self._patch_generate("Doe2020Title"):
            artifact = MagicMock()
            artifact.pdf_file = MagicMock()
            artifact.pdf_file.name = "publications/Doe2020Title.pdf"
            artifact.raw_file = None
            artifact.thumbnail = MagicMock()
            artifact.thumbnail.name = "thumbnails/StaleName.jpg"
            self.assertTrue(Artifact.do_filenames_need_updating(artifact))


class ArtifactRawFileLabelTests(SimpleTestCase):
    """
    Regression tests for Artifact.raw_file_label (issue #1152).

    The talk snippet previously hardcoded "PPTX" next to the raw_file
    download link, mislabeling .key (Keynote) and any other format. The
    label is derived from the file extension.
    """

    def _artifact_with_raw_file(self, name):
        from website.models.artifact import Artifact
        artifact = MagicMock(spec=Artifact)
        artifact.raw_file = MagicMock() if name else None
        if name:
            artifact.raw_file.name = name
        artifact.RAW_FILE_LABELS = Artifact.RAW_FILE_LABELS
        return artifact

    def _label(self, name):
        from website.models.artifact import Artifact
        return Artifact.raw_file_label.fget(self._artifact_with_raw_file(name))

    def test_pptx_label(self):
        self.assertEqual(self._label("talks/Doe2020Title.pptx"), "PPTX")

    def test_keynote_label(self):
        self.assertEqual(self._label("talks/Doe2020Title.key"), "Keynote")

    def test_ai_label(self):
        self.assertEqual(self._label("posters/Doe2020Title.ai"), "AI")

    def test_figma_label(self):
        self.assertEqual(self._label("talks/Doe2020Title.fig"), "Figma")

    def test_extension_case_insensitive(self):
        self.assertEqual(self._label("talks/Doe2020Title.PPTX"), "PPTX")
        self.assertEqual(self._label("talks/Doe2020Title.Key"), "Keynote")

    def test_unknown_extension_falls_back_to_uppercased_ext(self):
        self.assertEqual(self._label("talks/Doe2020Title.odp"), "ODP")

    def test_no_raw_file_returns_none(self):
        self.assertIsNone(self._label(None))

    def test_no_extension_returns_none(self):
        self.assertIsNone(self._label("talks/Doe2020Title"))


# ===========================================================================
# Database-backed test infrastructure (#1267)
# ===========================================================================
#
# Everything above this line uses SimpleTestCase + MagicMock — no DB, fast.
# Tests below this line use Django's TestCase, which wraps each test in a
# transaction that's rolled back at the end. They exercise real model code,
# real querysets, and the URL/view layer.
#
# Why this exists: several 2.3.4 fixes (publications prefetch_related,
# news null-author guards, delete_unused_files .path guards) shipped
# without regression tests because the bugs were only reachable through a
# real queryset or view. The classes below establish the foundation for
# backfilling that coverage incrementally. See #1267 for the broader plan.

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse


# Minimal 1x1 GIF used to satisfy Person.image / Person.easter_egg without
# touching the filesystem. Person.save() picks a random Star Wars image when
# either field is empty, opening a real file from media/. Pre-setting both
# with this SimpleUploadedFile skips the fallback branch entirely.
_GIF_1PX = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00"
    b"!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01"
    b"\x00\x00\x02\x02D\x01\x00;"
)


def _make_image_upload(name):
    """Return a SimpleUploadedFile that satisfies an ImageField."""
    return SimpleUploadedFile(name, _GIF_1PX, content_type="image/gif")


class DatabaseTestCase(TestCase):
    """
    Shared base for tests that touch the database. Provides small fixture
    helpers (make_person / make_publication / make_news_item) built on
    plain Model.objects.create() — no third-party fixture library. Each
    test runs inside a transaction and is rolled back, so tests stay
    isolated without manual cleanup.

    Why a base class instead of module-level helpers: subclasses can
    override the defaults in setUp() and the helpers can grow without
    cluttering the module namespace.
    """

    def make_person(self, first_name="Jane", last_name="Doe", **kwargs):
        """
        Create and return a Person. Image fields are pre-populated to
        skip Person.save()'s Star Wars fallback (which reads a real file
        from media/). Override by passing image=... explicitly.
        """
        from website.models import Person
        kwargs.setdefault(
            "image", _make_image_upload(f"{first_name}_{last_name}.gif")
        )
        kwargs.setdefault(
            "easter_egg",
            _make_image_upload(f"{first_name}_{last_name}_egg.gif"),
        )
        return Person.objects.create(
            first_name=first_name, last_name=last_name, **kwargs
        )

    def make_publication(self, title="A Test Paper", year=2024, **kwargs):
        """
        Create and return a Publication with sensible defaults: post-lab-
        formation date, conference venue, a forum name, and a dummy PDF
        (display_pub_snippet.html unconditionally renders pub.pdf_file.url,
        so tests that go through the publications view need one to render).
        Override via kwargs.
        """
        from datetime import date as _date
        from website.models import Publication
        from website.models.publication import PubType
        kwargs.setdefault("date", _date(year, 1, 1))
        kwargs.setdefault("forum_name", "CHI")
        kwargs.setdefault("pub_venue_type", PubType.CONFERENCE)
        kwargs.setdefault(
            "pdf_file",
            SimpleUploadedFile(
                f"{title.replace(' ', '_')}.pdf",
                b"%PDF-1.4 test",
                content_type="application/pdf",
            ),
        )
        return Publication.objects.create(title=title, **kwargs)

    def make_talk(self, title="A Test Talk", year=2024, **kwargs):
        """
        Create and return a Talk. Artifact.save() generates a thumbnail
        from pdf_file (via ImageMagick) on every save, so we provide a
        small valid PDF and let it run; tests that don't care about the
        thumbnail just ignore it.
        """
        from datetime import date as _date
        from website.models import Talk
        from website.models.talk import TalkType
        kwargs.setdefault("date", _date(year, 1, 1))
        kwargs.setdefault("forum_name", "CHI")
        kwargs.setdefault("talk_type", TalkType.CONFERENCE_TALK)
        kwargs.setdefault(
            "pdf_file",
            SimpleUploadedFile(
                f"{title.replace(' ', '_')}.pdf",
                b"%PDF-1.4 test",
                content_type="application/pdf",
            ),
        )
        return Talk.objects.create(title=title, **kwargs)

    def make_news_item(self, title="Test News", author=None, **kwargs):
        """
        Create and return a News item. `author` is intentionally optional
        (the FK is nullable with on_delete=SET_NULL) so tests can exercise
        the authorless code path that caused the original /news/158/ bug.
        """
        from datetime import date as _date
        from website.models import News
        kwargs.setdefault("date", _date(2024, 1, 1))
        kwargs.setdefault("content", "Test news body.")
        return News.objects.create(title=title, author=author, **kwargs)


# --- View-level: null author on /news/<id>/ (regression for #1013) --------


class NewsItemNullAuthorViewTests(DatabaseTestCase):
    """
    Regression for #1013 — a News item with author=None used to crash the
    news_item view with AttributeError on cur_news_item.author.authored_news.
    Fixed in 1c0d6c0 by guarding the access. This test pins the behavior
    so it can't regress silently.
    """

    def test_news_item_with_null_author_renders_200(self):
        item = self.make_news_item(title="Authorless News", author=None)
        response = self.client.get(
            reverse("website:news_item_by_id", kwargs={"id": item.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Authorless News")

    def test_news_item_with_author_still_renders_200(self):
        """Sanity check: the non-null path also works."""
        author = self.make_person(first_name="Ada", last_name="Lovelace")
        item = self.make_news_item(
            title="Authored News", author=author
        )
        response = self.client.get(
            reverse("website:news_item_by_id", kwargs={"id": item.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Authored News")


# --- Talk snippet: external_slides_url rendering (#1273) -----------------


class TalkExternalSlidesUrlTests(DatabaseTestCase):
    """
    Pins the rendering of Talk.external_slides_url in
    snippets/display_talk_snippet.html — the "Source" link should appear
    only when the URL is set. Also pins that Poster persists the field
    (no display surface for posters yet, but the column must exist).
    """

    def _render_talk_snippet(self, talk):
        from django.template.loader import render_to_string
        return render_to_string(
            "snippets/display_talk_snippet.html",
            {"talk": talk, "MEDIA_URL": "/media/"},
        )

    def test_source_link_renders_when_external_slides_url_set(self):
        talk = self.make_talk(
            title="Figma Talk",
            external_slides_url="https://www.figma.com/file/abc123/slides",
        )
        html = self._render_talk_snippet(talk)
        self.assertIn("https://www.figma.com/file/abc123/slides", html)
        self.assertIn("fa-up-right-from-square", html)
        # opens-in-new-tab affordance must be present for accessibility
        self.assertIn('target="_blank"', html)
        self.assertIn('rel="noopener"', html)

    def test_source_link_absent_when_external_slides_url_blank(self):
        talk = self.make_talk(title="No-Source Talk")
        html = self._render_talk_snippet(talk)
        self.assertNotIn("fa-up-right-from-square", html)

    def test_poster_external_slides_url_round_trips(self):
        """Schema pin: Poster.external_slides_url must persist to the DB."""
        from website.models import Poster
        poster = Poster.objects.create(
            title="A Test Poster",
            external_slides_url="https://www.figma.com/file/xyz/poster",
            pdf_file=SimpleUploadedFile(
                "test_poster.pdf",
                b"%PDF-1.4 test",
                content_type="application/pdf",
            ),
        )
        reloaded = Poster.objects.get(pk=poster.pk)
        self.assertEqual(
            reloaded.external_slides_url,
            "https://www.figma.com/file/xyz/poster",
        )


# --- Query-count: /publications/ prefetch_related (regression for d4f6d65) -


class PublicationsViewQueryCountTests(DatabaseTestCase):
    """
    Pins the prefetch_related batch on /publications/ (d4f6d65).

    Before the fix, the snippet template iterated pub.authors.all and
    pub.projects.all per publication, producing 617 queries on prod with
    ~250 pubs. The fix added .prefetch_related('authors', 'projects',
    'keywords') to the view's queryset, dropping that to 60.

    The key correctness property is that the query count is bounded by a
    constant — it must NOT grow with the number of publications. This
    test creates publications with M2M relations and asserts the count
    stays under a generous ceiling for two different data sizes. If a
    future contributor removes the prefetches, the count climbs linearly
    and the larger-N test fails.
    """

    # Generous ceiling well above the steady-state count we measured
    # locally (~15 queries for the publications view). The ceiling exists
    # to catch order-of-magnitude regressions, not to pin an exact count.
    QUERY_CEILING = 30

    def _seed_publications(self, count):
        author = self.make_person(first_name="Ada", last_name="Lovelace")
        for i in range(count):
            pub = self.make_publication(
                title=f"Paper {i}", year=2024
            )
            pub.authors.add(author)

    def _capture_publications_query_count(self):
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(reverse("website:publications"))
        return response, len(ctx.captured_queries)

    def test_query_count_is_bounded_with_few_pubs(self):
        self._seed_publications(2)
        response, count = self._capture_publications_query_count()
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(
            count,
            self.QUERY_CEILING,
            msg=f"Query count {count} exceeded ceiling {self.QUERY_CEILING}",
        )

    def test_query_count_does_not_grow_with_pub_count(self):
        """
        The real regression guard: query count must be roughly the same
        whether we render 2 pubs or 20. If prefetches are removed, the
        count grows by a multiple of N and this test will fail.
        """
        self._seed_publications(20)
        response, count = self._capture_publications_query_count()
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(
            count,
            self.QUERY_CEILING,
            msg=(
                f"Query count {count} exceeded ceiling {self.QUERY_CEILING} "
                "with 20 publications — prefetch_related likely regressed"
            ),
        )


# --- Data Health admin dashboard + checks (issue #1276) -------------------

import os
import shutil
import tempfile

from django.contrib.auth.models import User
from django.test import override_settings

from website.admin.data_health.registry import get_check
from website.utils.name_utils import normalize_person_name, is_default_person_image


class NameUtilsTests(SimpleTestCase):
    """Unit tests for the shared name/image helpers (no DB)."""

    def test_normalize_folds_accents_and_strips_nonalpha(self):
        self.assertEqual(normalize_person_name("Jon", "Froehlich"), "jonfroehlich")
        self.assertEqual(normalize_person_name("Renée", "O'Brien"), "reneeobrien")
        self.assertEqual(normalize_person_name("Jon-Paul", "Smith Jr."), "jonpaulsmithjr")

    def test_same_name_different_case_same_key(self):
        self.assertEqual(
            normalize_person_name("Jane", "Doe"),
            normalize_person_name("jane", "doe"),
        )

    def test_default_image_detection(self):
        self.assertTrue(is_default_person_image(None))

        class _Empty:
            name = ""

        class _StarWars:
            name = "person/jane_doe_easteregg_starwars_rebel.png"

        class _Real:
            name = "person/jane_doe.gif"

        self.assertTrue(is_default_person_image(_Empty()))
        self.assertTrue(is_default_person_image(_StarWars()))
        self.assertFalse(is_default_person_image(_Real()))


class DataHealthAuthTests(DatabaseTestCase):
    """Superuser gating on the dashboard, detail, and export views."""

    def setUp(self):
        self.superuser = User.objects.create_superuser("root", "r@example.com", "pw")
        self.staff = User.objects.create_user(
            "staffer", "s@example.com", "pw", is_staff=True
        )

    def test_superuser_can_view_dashboard(self):
        self.client.force_login(self.superuser)
        resp = self.client.get(reverse("admin:data_health_dashboard"))
        self.assertEqual(resp.status_code, 200)

    def test_staff_nonsuperuser_forbidden(self):
        self.client.force_login(self.staff)
        for name, args in [
            ("admin:data_health_dashboard", []),
            ("admin:data_health_detail", ["duplicate-people"]),
            ("admin:data_health_export", ["duplicate-people"]),
        ]:
            resp = self.client.get(reverse(name, args=args))
            self.assertEqual(resp.status_code, 403, msg=name)

    def test_anonymous_redirected_to_login(self):
        resp = self.client.get(reverse("admin:data_health_dashboard"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/admin/login/", resp["Location"])

    def test_unknown_check_returns_404(self):
        self.client.force_login(self.superuser)
        resp = self.client.get(reverse("admin:data_health_detail", args=["nope"]))
        self.assertEqual(resp.status_code, 404)


class DataHealthCsvTests(DatabaseTestCase):
    """The CSV export streams text/csv as an attachment with the right rows."""

    def setUp(self):
        self.superuser = User.objects.create_superuser("root", "r@example.com", "pw")
        self.client.force_login(self.superuser)

    def test_csv_headers_and_content(self):
        self.make_person(first_name="Jane", last_name="Doe", email="jane@example.com")
        self.make_person(first_name="Jane", last_name="Doe", email="jane2@example.com")
        resp = self.client.get(
            reverse("admin:data_health_export", args=["duplicate-people"])
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "text/csv")
        self.assertIn(
            'attachment; filename="duplicate-people-', resp["Content-Disposition"]
        )
        body = resp.content.decode()
        self.assertIn("cluster_key", body)  # header row
        self.assertIn("jane@example.com", body)
        self.assertIn("jane2@example.com", body)


class DuplicatePeopleCheckTests(DatabaseTestCase):
    def test_clusters_only_multi_person_same_name(self):
        self.make_person(first_name="Jane", last_name="Doe")
        self.make_person(first_name="Jane", last_name="Doe")
        self.make_person(first_name="John", last_name="Smith")  # unique
        rows = get_check("duplicate-people").get_rows()
        self.assertEqual({r["cluster_key"] for r in rows}, {"janedoe"})
        self.assertEqual(len(rows), 2)

    def test_total_refs_counts_relations(self):
        p1 = self.make_person(first_name="Jane", last_name="Doe")
        p2 = self.make_person(first_name="Jane", last_name="Doe")
        pub = self.make_publication(title="A Counted Paper")
        pub.authors.add(p1)
        rows = {r["id"]: r for r in get_check("duplicate-people").get_rows()}
        self.assertEqual(rows[p1.pk]["pub_count"], 1)
        self.assertEqual(rows[p1.pk]["total_refs"], 1)
        self.assertEqual(rows[p2.pk]["total_refs"], 0)  # safe-to-delete shell

    def test_clean_data_no_rows(self):
        self.make_person(first_name="Solo", last_name="Person")
        self.assertEqual(get_check("duplicate-people").get_rows(), [])


class UrlNameCollisionsCheckTests(DatabaseTestCase):
    def test_detects_forced_collision_and_placeholder(self):
        from website.models import Person

        self.make_person(first_name="Jane", last_name="Doe")
        p2 = self.make_person(first_name="Jane", last_name="Doe")  # -> janedoe2
        p3 = self.make_person(first_name="Solo", last_name="One")
        # save() auto-dedupes url_name, so force a historical collision directly.
        Person.objects.filter(pk=p2.pk).update(url_name="janedoe")
        Person.objects.filter(pk=p3.pk).update(url_name="placeholder")

        rows = {r["url_name"]: r for r in get_check("url-name-collisions").get_rows()}
        self.assertIn("janedoe", rows)
        self.assertEqual(rows["janedoe"]["count"], 2)
        self.assertIn("placeholder", rows)


class PublicationQualityCheckTests(DatabaseTestCase):
    def test_duplicate_titles_and_missing_venue(self):
        self.make_publication(title="Dup Paper")
        self.make_publication(title="Dup Paper")  # duplicate normalized title
        self.make_publication(title="No Venue Paper", forum_name=None)
        rows = {r["id"]: r for r in get_check("publication-quality").get_rows()}
        self.assertEqual(len([r for r in rows.values() if r["dup_title"]]), 2)
        self.assertTrue(
            any("forum_name" in r["missing_fields"] for r in rows.values())
        )


class ProjectHealthCheckTests(DatabaseTestCase):
    def test_flags_incomplete_project(self):
        from website.models import Project

        Project.objects.create(name="Lonely Project", short_name="lonely")
        rows = {r["name"]: r for r in get_check("project-health").get_rows()}
        self.assertIn("Lonely Project", rows)
        self.assertIn("no thumbnail", rows["Lonely Project"]["issues"])
        self.assertIn("no publication", rows["Lonely Project"]["issues"])


class PositionIntegrityCheckTests(DatabaseTestCase):
    def test_no_position_and_self_advisor(self):
        from datetime import date as _date

        from website.models import Position
        from website.models.position import Title

        p_nopos = self.make_person(first_name="No", last_name="Position")
        p_self = self.make_person(first_name="Self", last_name="Advisor")
        Position.objects.create(
            person=p_self,
            start_date=_date(2020, 1, 1),
            title=Title.PHD_STUDENT,
            advisor=p_self,
        )
        issues = {
            (r["person_id"], r["issue"])
            for r in get_check("position-integrity").get_rows()
        }
        self.assertIn((p_nopos.pk, "no position"), issues)
        self.assertIn((p_self.pk, "self-advisor"), issues)


class NewsHealthCheckTests(DatabaseTestCase):
    def test_flags_missing_slug_and_author(self):
        from website.models import News

        author = self.make_person(first_name="News", last_name="Writer")
        n_noauthor = self.make_news_item(title="Orphan News", author=None)
        n_noslug = self.make_news_item(title="Slugless News", author=author)
        News.objects.filter(pk=n_noslug.pk).update(slug="")  # save() auto-slugs

        rows = {r["id"]: r for r in get_check("news-health").get_rows()}
        self.assertIn(n_noauthor.pk, rows)
        self.assertFalse(rows[n_noauthor.pk]["has_author"])
        self.assertIn(n_noslug.pk, rows)
        self.assertTrue(rows[n_noslug.pk]["missing_slug"])


class MediaIntegrityCheckTests(DatabaseTestCase):
    def setUp(self):
        # Use a throwaway MEDIA_ROOT so the test never pollutes dev media.
        self._media_dir = tempfile.mkdtemp(prefix="dh_media_")
        self._override = override_settings(MEDIA_ROOT=self._media_dir)
        self._override.enable()
        self.addCleanup(self._override.disable)
        self.addCleanup(shutil.rmtree, self._media_dir, ignore_errors=True)

    def test_flags_missing_file(self):
        pub = self.make_publication(title="Vanishing Paper")
        path = pub.pdf_file.path
        if os.path.exists(path):
            os.remove(path)  # simulate a file that disappeared from disk
        hits = [
            r
            for r in get_check("media-integrity").get_rows()
            if r["type"] == "Publication"
            and r["id"] == pub.pk
            and r["status"] == "missing-file"
        ]
        self.assertTrue(hits)


class DataHealthReadOnlyTests(DatabaseTestCase):
    def test_get_rows_does_not_mutate_db(self):
        from website.models import Person, Publication

        self.make_person(first_name="Jane", last_name="Doe")
        self.make_person(first_name="Jane", last_name="Doe")
        before = (Person.objects.count(), Publication.objects.count())
        for slug in ("duplicate-people", "url-name-collisions", "position-integrity"):
            get_check(slug).get_rows()
        after = (Person.objects.count(), Publication.objects.count())
        self.assertEqual(before, after)
