"""
Pins the admin-facing labels on Position fields whose DB column names are
deliberately *not* what editors should see.

The columns keep their historical names because this repo regenerates migrations
non-interactively per environment, where a field rename can't be confirmed and
would drop the column — so each of these was fixed with verbose_name, which
carries no schema change. These tests keep a future edit from silently reverting
to the auto-generated label.
"""

from django.test import SimpleTestCase

from website.models import Person, Position


class MentorLabelTests(SimpleTestCase):
    """Issue #806: the mentor dropdown is no longer grad-only (see
    get_active_mentors_queryset), so ``grad_mentor`` is labeled just "Mentor"."""

    def test_grad_mentor_field_labeled_mentor(self):
        field = Position._meta.get_field("grad_mentor")
        self.assertEqual(field.verbose_name, "Mentor")


class AffiliationLabelTests(SimpleTestCase):
    """``school``/``department`` also hold non-academic affiliations (nonprofits,
    companies, medical centers), so "School" was the wrong prompt to give editors."""

    def test_school_field_labeled_institution_or_organization(self):
        field = Position._meta.get_field("school")
        self.assertEqual(field.verbose_name, "Institution or organization")
        self.assertTrue(field.help_text)

    def test_department_field_labeled_department_or_unit(self):
        field = Position._meta.get_field("department")
        self.assertEqual(field.verbose_name, "Department or unit")
        self.assertTrue(field.help_text)

    def test_person_admin_columns_match_the_field_labels(self):
        self.assertEqual(
            Person.get_current_school.short_description, "Institution or organization"
        )
        self.assertEqual(
            Person.get_current_department.short_description, "Department or unit"
        )
