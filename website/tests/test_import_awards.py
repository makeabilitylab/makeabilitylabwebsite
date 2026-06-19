"""
Regression tests for the `import_awards` management command (#awards-update).

The command runs on every container start (docker-entrypoint.sh), so the
guarantees that matter are: it's idempotent, it never crashes on a recipient/
project name that doesn't resolve, `--dry-run` writes nothing, and it applies
the one in-place data fix (#audit-F) exactly once.
"""

from datetime import date

from django.core.management import call_command

from website.models import Award
from website.models.award import AwardType
from website.tests.base import DatabaseTestCase


class ImportAwardsTests(DatabaseTestCase):

    def test_creates_award_for_resolved_recipient(self):
        jon = self.make_person(first_name="Jon", last_name="Froehlich")
        call_command("import_awards", verbosity=0)

        career = Award.objects.filter(title="NSF CAREER Award", date=date(2017, 2, 14)).first()
        self.assertIsNotNone(career)
        self.assertEqual(career.award_type, AwardType.FACULTY_HONOR)
        self.assertIn(jon, career.recipients.all())

    def test_is_idempotent(self):
        self.make_person(first_name="Jon", last_name="Froehlich")
        call_command("import_awards", verbosity=0)
        count_after_first = Award.objects.count()
        self.assertGreater(count_after_first, 0)

        call_command("import_awards", verbosity=0)
        self.assertEqual(Award.objects.count(), count_after_first)

    def test_skips_entries_whose_honorees_do_not_resolve(self):
        # No people/projects exist, so every entry lacking a resolvable honoree
        # is skipped rather than created empty — and nothing raises.
        call_command("import_awards", verbosity=0)
        for award in Award.objects.all():
            self.assertTrue(
                award.recipients.exists() or award.projects.exists(),
                f"{award.title} was created with no honoree",
            )

    def test_dry_run_writes_nothing(self):
        self.make_person(first_name="Jon", last_name="Froehlich")
        call_command("import_awards", "--dry-run", verbosity=0)
        self.assertEqual(Award.objects.count(), 0)

    def test_fixes_stale_facilitators_choice_row(self):
        prototypar = self.make_project(name="PrototypAR", is_visible=True)
        self.make_person(first_name="Seokbin", last_name="Kang")
        stale = Award.objects.create(
            title="Facilitators’ Choice Award, NSF Video Showcase",
            organization="NSF Video Showcase",
            date=date(2020, 5, 20),
            award_type=AwardType.PROJECT_AWARD,
            description="Awarded to 21 of 242 video submissions (8.7%)",
        )

        call_command("import_awards", verbosity=0)

        stale.refresh_from_db()
        self.assertEqual(stale.date, date(2019, 5, 31))
        self.assertIn(prototypar, stale.projects.all())

        # Running again must not re-touch it (it's no longer dated 2020).
        call_command("import_awards", verbosity=0)
        stale.refresh_from_db()
        self.assertEqual(stale.date, date(2019, 5, 31))
