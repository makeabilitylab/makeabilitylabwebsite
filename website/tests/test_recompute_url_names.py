"""
Regression tests for url_name de-collision (#1206 / #1275):

- the recompute_url_names management command,
- the refactored Person.save() derivation (middle-initial / numeric), and
- the hardened member view (clean 404 instead of a 500 or silent .first()).
"""

from django.core.management import call_command
from django.urls import reverse

from website.models import Person
from website.tests.base import DatabaseTestCase


def _force_shared_url_name(*people, url_name):
    """Simulate historical pre-collision-loop rows sharing a bare url_name
    (bypasses Person.save(), which would otherwise auto-de-collide)."""
    Person.objects.filter(pk__in=[p.pk for p in people]).update(url_name=url_name)


class RecomputeUrlNamesCommandTests(DatabaseTestCase):
    def test_decollides_to_distinct_url_names(self):
        a = self.make_person("Jiahao", "Li")
        b = self.make_person("Jiahao", "Li")  # a.pk < b.pk
        _force_shared_url_name(a, b, url_name="jiahaoli")

        call_command('recompute_url_names')

        a.refresh_from_db()
        b.refresh_from_db()
        self.assertEqual(a.url_name, "jiahaoli")   # earliest keeps the bare name
        self.assertEqual(b.url_name, "jiahaoli2")  # no middle name -> numeric suffix

    def test_prefers_middle_initial_differentiator(self):
        a = self.make_person("Jasmine", "Zhang")
        b = self.make_person("Jasmine", "Zhang", middle_name="Xin")
        _force_shared_url_name(a, b, url_name="jasminezhang")

        call_command('recompute_url_names')

        a.refresh_from_db()
        b.refresh_from_db()
        self.assertEqual(a.url_name, "jasminezhang")
        self.assertEqual(b.url_name, "jasminexzhang")

    def test_is_idempotent(self):
        a = self.make_person("Jiahao", "Li")
        b = self.make_person("Jiahao", "Li")
        _force_shared_url_name(a, b, url_name="jiahaoli")

        call_command('recompute_url_names')
        first = list(Person.objects.order_by('pk').values_list('url_name', flat=True))
        call_command('recompute_url_names')
        second = list(Person.objects.order_by('pk').values_list('url_name', flat=True))
        self.assertEqual(first, second)

    def test_dry_run_changes_nothing(self):
        a = self.make_person("Jiahao", "Li")
        b = self.make_person("Jiahao", "Li")
        _force_shared_url_name(a, b, url_name="jiahaoli")

        call_command('recompute_url_names', dry_run=True)

        a.refresh_from_db()
        b.refresh_from_db()
        self.assertEqual(a.url_name, "jiahaoli")
        self.assertEqual(b.url_name, "jiahaoli")  # untouched


class PersonSaveUrlNameTests(DatabaseTestCase):
    def test_new_namesake_with_middle_name_gets_middle_initial(self):
        self.make_person("Jasmine", "Zhang")  # claims jasminezhang
        b = self.make_person("Jasmine", "Zhang", middle_name="Xin")
        self.assertEqual(b.url_name, "jasminexzhang")

    def test_new_namesake_without_middle_name_gets_numeric_suffix(self):
        self.make_person("Jiahao", "Li")
        b = self.make_person("Jiahao", "Li")
        self.assertEqual(b.url_name, "jiahaoli2")


class MemberViewCollisionTests(DatabaseTestCase):
    def test_namesakes_each_resolve_200_after_recompute(self):
        a = self.make_person("Jiahao", "Li")
        b = self.make_person("Jiahao", "Li")
        _force_shared_url_name(a, b, url_name="jiahaoli")
        call_command('recompute_url_names')

        a.refresh_from_db()
        b.refresh_from_db()
        for person in (a, b):
            url = reverse('website:member_by_name', kwargs={'member_name': person.url_name})
            self.assertEqual(self.client.get(url).status_code, 200)

    def test_unresolved_collision_returns_404_not_500(self):
        a = self.make_person("Jiahao", "Li")
        b = self.make_person("Jiahao", "Li")
        _force_shared_url_name(a, b, url_name="jiahaoli")

        url = reverse('website:member_by_name', kwargs={'member_name': 'jiahaoli'})
        self.assertEqual(self.client.get(url).status_code, 404)
