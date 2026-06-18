"""
Regression tests for the merge_duplicate_people management command (#1275).

Verifies that merging a duplicate Person B into a canonical Person A relocates
EVERY relation type (FK, the advisor self-references, sorted-M2M author sets,
plain M2M), preserves publication author order, backfills only-blank scalar
fields, and is both dry-run-safe and idempotent.
"""

import csv
import tempfile
from datetime import date

from django.core.management import call_command

from website.models import (
    Award,
    Grant,
    News,
    Person,
    Position,
    ProjectRole,
    Sponsor,
)
from website.models.position import Title
from website.tests.base import DatabaseTestCase


def _decisions_file(rows):
    """Write a decisions CSV to a temp path and return it."""
    fh = tempfile.NamedTemporaryFile(
        mode='w', suffix='.csv', delete=False, newline='', encoding='utf-8')
    writer = csv.DictWriter(fh, fieldnames=['source_id', 'action', 'target_id', 'note'])
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    fh.close()
    return fh.name


class MergeDuplicatePeopleTests(DatabaseTestCase):
    def setUp(self):
        # A = canonical/target, B = duplicate/source.
        self.target = self.make_person("Jennifer", "Mankoff")
        self.source = self.make_person("Jennifer", "Mankoff")

    def _merge(self, apply=True, action='merge', target_id=None):
        path = _decisions_file([{
            'source_id': self.source.pk,
            'action': action,
            'target_id': target_id if target_id is not None else self.target.pk,
            'note': 'test',
        }])
        call_command('merge_duplicate_people', decisions=path, apply=apply)

    # ----- FK + advisor self-ref reassignment --------------------------------

    def test_merge_reassigns_fk_and_advisor_self_refs(self):
        other = self.make_person("Some", "Advisee")
        # B is the person on one position, and the advisor on another.
        own = Position.objects.create(
            person=self.source, start_date=date(2020, 1, 1), title=Title.PHD_STUDENT)
        advised = Position.objects.create(
            person=other, advisor=self.source, co_advisor=self.source,
            grad_mentor=self.source, start_date=date(2020, 1, 1), title=Title.PHD_STUDENT)
        project = self.make_project("Proj")
        role = ProjectRole.objects.create(
            person=self.source, project=project, start_date=date(2020, 1, 1))
        news = self.make_news_item(author=self.source)

        self._merge()

        self.assertFalse(Person.objects.filter(pk=self.source.pk).exists())
        own.refresh_from_db()
        advised.refresh_from_db()
        role.refresh_from_db()
        news.refresh_from_db()
        self.assertEqual(own.person, self.target)
        self.assertEqual(advised.advisor, self.target)
        self.assertEqual(advised.co_advisor, self.target)
        self.assertEqual(advised.grad_mentor, self.target)
        self.assertEqual(role.person, self.target)
        self.assertEqual(news.author, self.target)

    # ----- sorted-M2M order preservation + dedup -----------------------------

    def test_merge_preserves_publication_author_order(self):
        first = self.make_person("Aa", "Author")
        last = self.make_person("Zz", "Author")
        pub = self.make_publication()
        pub.authors.set([first, self.source, last])  # B sits in the middle slot

        self._merge()

        pub.refresh_from_db()
        # A takes B's exact position; order otherwise unchanged.
        self.assertEqual(list(pub.authors.all()), [first, self.target, last])

    def test_merge_dedupes_when_target_already_coauthor(self):
        pub = self.make_publication()
        pub.authors.set([self.source, self.target])  # both already on the paper

        self._merge()

        pub.refresh_from_db()
        self.assertEqual(list(pub.authors.all()), [self.target])

    def test_merge_moves_award_recipients_and_grant_authors(self):
        award = Award.objects.create(title="Best Paper", date=date(2020, 1, 1))
        award.recipients.set([self.source])
        grant = Grant.objects.create(
            sponsor=Sponsor.objects.create(name="NSF"),
            title="A Grant", date=date(2020, 1, 1))
        grant.authors.set([self.source])

        self._merge()

        award.refresh_from_db()
        grant.refresh_from_db()
        self.assertEqual(list(award.recipients.all()), [self.target])
        self.assertEqual(list(grant.authors.all()), [self.target])

    def test_merge_moves_plain_news_people_m2m(self):
        news = self.make_news_item()
        news.people.set([self.source])

        self._merge()

        news.refresh_from_db()
        self.assertEqual(list(news.people.all()), [self.target])

    # ----- scalar backfill ---------------------------------------------------

    def test_scalar_backfill_fills_blanks_only(self):
        Person.objects.filter(pk=self.target.pk).update(
            email="keep@uw.edu", github="")
        Person.objects.filter(pk=self.source.pk).update(
            email="lose@uw.edu", github="sourcehub")

        self._merge()

        self.target.refresh_from_db()
        self.assertEqual(self.target.email, "keep@uw.edu")   # populated: untouched
        self.assertEqual(self.target.github, "sourcehub")    # blank: backfilled

    # ----- safety: dry-run + idempotency -------------------------------------

    def test_dry_run_makes_no_changes(self):
        pub = self.make_publication()
        pub.authors.set([self.source])

        self._merge(apply=False)

        self.assertTrue(Person.objects.filter(pk=self.source.pk).exists())
        pub.refresh_from_db()
        self.assertEqual(list(pub.authors.all()), [self.source])

    def test_second_apply_is_a_noop(self):
        self.make_news_item(author=self.source)
        self._merge()
        self.assertFalse(Person.objects.filter(pk=self.source.pk).exists())
        # Re-running the same decisions file must not raise and must change nothing.
        self._merge()
        self.assertFalse(Person.objects.filter(pk=self.source.pk).exists())
        self.assertTrue(Person.objects.filter(pk=self.target.pk).exists())

    def test_name_mismatch_is_refused_by_default(self):
        # A prod-id decisions file run against the wrong DB would pair unrelated
        # people; the name guard must refuse rather than corrupt data.
        other = self.make_person("Totally", "Different")
        news = self.make_news_item(author=self.source)
        path = _decisions_file([{
            'source_id': self.source.pk, 'action': 'merge',
            'target_id': other.pk, 'note': 'mismatch'}])
        call_command('merge_duplicate_people', decisions=path, apply=True)
        # Refused: source survives, its relation untouched.
        self.assertTrue(Person.objects.filter(pk=self.source.pk).exists())
        news.refresh_from_db()
        self.assertEqual(news.author, self.source)

    def test_name_mismatch_allowed_with_flag(self):
        other = self.make_person("Totally", "Different")
        self.make_news_item(author=self.source)
        path = _decisions_file([{
            'source_id': self.source.pk, 'action': 'merge',
            'target_id': other.pk, 'note': 'cross-name'}])
        call_command('merge_duplicate_people', decisions=path, apply=True,
                     allow_name_mismatch=True)
        self.assertFalse(Person.objects.filter(pk=self.source.pk).exists())

    def test_delete_action_refuses_when_refs_exist(self):
        self.make_news_item(author=self.source)
        path = _decisions_file([{
            'source_id': self.source.pk, 'action': 'delete',
            'target_id': '', 'note': 'shell?'}])
        call_command('merge_duplicate_people', decisions=path, apply=True)
        # Has a reference, so delete is refused — source survives.
        self.assertTrue(Person.objects.filter(pk=self.source.pk).exists())
