"""
Regression tests for issue #1126.

When an admin edits a Person and sets an advisor / co-advisor / mentor on an
inline Position, the dropdown must only offer role-appropriate people:

  - advisor / co_advisor  -> currently active professors only
  - grad_mentor ("Mentor") -> currently active senior lab members only

The plain ``advisor`` <select> is filtered by
``PositionInline.formfield_for_foreignkey``. But ``co_advisor`` and
``grad_mentor`` are ``autocomplete_fields``: their options come from the
admin autocomplete JSON endpoint (``AutocompleteJsonView`` -> the *target*
model admin's ``get_search_results``), which bypasses
``formfield_for_foreignkey`` entirely. Without a ``get_search_results``
filter on ``PersonAdmin``, the autocomplete search returns *every* person
(undergrads included), which is the bug reported in #1126.

These tests hit the real autocomplete endpoint and assert the role filtering
holds for all three fields.
"""

from datetime import date

from django.contrib.auth import get_user_model
from django.urls import reverse

from website.models import Person, Position
from website.models.position import Title
from website.tests.base import DatabaseTestCase


class AdvisorMentorAutocompleteTests(DatabaseTestCase):
    @classmethod
    def setUpTestData(cls):
        # An active full professor: valid advisor/co-advisor, also a valid mentor.
        cls.prof = Person.objects.create(first_name="Pat", last_name="Professor")
        Position.objects.create(person=cls.prof, start_date=date(2015, 1, 1),
                                end_date=None, title=Title.FULL_PROF)

        # An active PhD student: a valid mentor, but NOT a valid advisor.
        cls.phd = Person.objects.create(first_name="Parker", last_name="Phd")
        Position.objects.create(person=cls.phd, start_date=date(2021, 1, 1),
                                end_date=None, title=Title.PHD_STUDENT)

        # An active undergrad: NOT a valid advisor and NOT a valid mentor.
        cls.ugrad = Person.objects.create(first_name="Uma", last_name="Undergrad")
        Position.objects.create(person=cls.ugrad, start_date=date(2023, 1, 1),
                                end_date=None, title=Title.UGRAD)

    def setUp(self):
        super().setUp()
        User = get_user_model()
        User.objects.create_superuser("admin1126", "admin1126@example.com", "pw")
        self.client.login(username="admin1126", password="pw")

    def _autocomplete_ids(self, field_name, term=""):
        """Return the set of Person ids the admin autocomplete offers for the
        given Position FK field."""
        resp = self.client.get(
            reverse("admin:autocomplete"),
            {
                "app_label": "website",
                "model_name": "position",
                "field_name": field_name,
                "term": term,
            },
        )
        self.assertEqual(resp.status_code, 200)
        return {int(item["id"]) for item in resp.json()["results"]}

    def test_co_advisor_autocomplete_only_offers_active_professors(self):
        ids = self._autocomplete_ids("co_advisor")
        self.assertIn(self.prof.id, ids)
        self.assertNotIn(self.phd.id, ids)
        self.assertNotIn(self.ugrad.id, ids)

    def test_grad_mentor_autocomplete_only_offers_senior_members(self):
        # Mentors are senior lab members (postdoc/PhD/MS/research-scientist/etc.).
        # Professors are advisors, not mentors, so FULL_PROF is intentionally
        # excluded by get_active_mentors_queryset.
        ids = self._autocomplete_ids("grad_mentor")
        self.assertIn(self.phd.id, ids)
        self.assertNotIn(self.prof.id, ids)
        self.assertNotIn(self.ugrad.id, ids)
