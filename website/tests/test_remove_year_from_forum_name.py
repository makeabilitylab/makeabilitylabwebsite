"""
Tests for the remove_year_from_forum_name command (#1390).

The command strips a trailing year from artifact forum names across Talk,
Poster, and Publication. It originally ran on Publications only, which left
historical Talk/Poster forum names with embedded years (e.g. "ASSETS 2016") and
caused the standardized filename scheme to double the year
("...ASSETS20162016"). These tests pin the generalized behavior and, critically,
that cleaning a forum name does NOT rename the artifact's files (it must write
via QuerySet.update(), not Model.save(), so renaming stays under the separately
gated restandardize_artifact_filenames step).
"""

from django.core.management import call_command

from website.models import Talk, Publication
from website.tests.base import DatabaseTestCase


class RemoveYearFromForumNameTests(DatabaseTestCase):
    def test_strips_trailing_year_from_talk_forum_name(self):
        # Talks were previously skipped entirely; this is the core regression.
        talk = self.make_talk(forum_name="ASSETS 2016", year=2016)

        call_command("remove_year_from_forum_name")

        talk.refresh_from_db()
        self.assertEqual(talk.forum_name, "ASSETS")

    def test_strips_year_with_no_separating_space(self):
        # remove_trailing_year matches \d{4}$ with no separator, so the
        # space-free embedded form is cleaned too.
        talk = self.make_talk(forum_name="ASSETS2016", year=2016)

        call_command("remove_year_from_forum_name")

        talk.refresh_from_db()
        self.assertEqual(talk.forum_name, "ASSETS")

    def test_cleaning_forum_name_does_not_rename_files(self):
        # The whole reason this command uses QuerySet.update(): a forum_name
        # change alters the generated standardized filename, and Model.save()
        # would rename the files on disk. update() must leave the files alone.
        alice = self.make_person(first_name="Alice", last_name="Smith")
        talk = self.make_talk(
            forum_name="ASSETS 2016", year=2016, authors=[alice]
        )
        pdf_name_before = talk.pdf_file.name

        call_command("remove_year_from_forum_name")

        talk.refresh_from_db()
        self.assertEqual(talk.forum_name, "ASSETS")
        # File path is untouched even though the standardized name changed.
        self.assertEqual(talk.pdf_file.name, pdf_name_before)

    def test_already_clean_forum_name_is_untouched_and_idempotent(self):
        talk = self.make_talk(forum_name="CHI", year=2020)
        pub = self.make_publication(forum_name="UIST", year=2021)

        # First run changes nothing; a second run is also a no-op.
        call_command("remove_year_from_forum_name")
        call_command("remove_year_from_forum_name")

        talk.refresh_from_db()
        pub.refresh_from_db()
        self.assertEqual(talk.forum_name, "CHI")
        self.assertEqual(pub.forum_name, "UIST")

    def test_dry_run_changes_nothing(self):
        talk = self.make_talk(forum_name="ASSETS 2016", year=2016)

        call_command("remove_year_from_forum_name", "--dry-run")

        talk.refresh_from_db()
        self.assertEqual(talk.forum_name, "ASSETS 2016")

    def test_running_twice_is_idempotent_after_a_real_change(self):
        talk = self.make_talk(forum_name="ASSETS 2016", year=2016)

        call_command("remove_year_from_forum_name")
        talk.refresh_from_db()
        self.assertEqual(talk.forum_name, "ASSETS")

        # Re-running must not strip further (no trailing year remains).
        call_command("remove_year_from_forum_name")
        talk.refresh_from_db()
        self.assertEqual(talk.forum_name, "ASSETS")
