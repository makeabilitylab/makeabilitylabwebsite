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
