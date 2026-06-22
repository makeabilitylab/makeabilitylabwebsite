"""
Regression test for issue #806.

The Position.grad_mentor field keeps its historical Python/DB name, but the
mentor dropdown is no longer grad-only (see get_active_mentors_queryset), so the
user-facing admin label was changed to simply "Mentor" via verbose_name. This
pins that label so a future edit to the field doesn't silently revert it to the
auto-generated "Grad mentor".
"""

from django.test import SimpleTestCase

from website.models import Position


class MentorLabelTests(SimpleTestCase):
    def test_grad_mentor_field_labeled_mentor(self):
        field = Position._meta.get_field("grad_mentor")
        self.assertEqual(field.verbose_name, "Mentor")
