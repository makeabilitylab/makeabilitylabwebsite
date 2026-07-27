"""
Regression tests for the quick links in the admin header (``userlinks`` block
of ``website/templates/admin/base_site.html``).

Two properties matter: (1) both ``{% url %}`` names still resolve—a rename
would raise ``NoReverseMatch`` and 500 *every* admin page, not just the linked
one; and (2) the Activity Log link stays superuser-only, matching the gate on
``LogEntryAdmin`` itself.
"""

from django.contrib.auth import get_user_model
from django.urls import reverse

from website.tests.base import DatabaseTestCase

User = get_user_model()


class AdminHeaderQuickLinkTests(DatabaseTestCase):
    """The admin header renders, and the Activity Log link is superuser-only."""

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="root", email="root@example.com", password="pw")
        self.editor = User.objects.create_user(
            username="editor", email="editor@example.com", password="pw",
            is_staff=True)

    def test_superuser_sees_both_quick_links(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("website:view_project_people"))
        self.assertContains(response, reverse("admin:admin_logentry_changelist"))

    def test_staff_non_superuser_does_not_see_activity_log(self):
        self.client.force_login(self.editor)
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("website:view_project_people"))
        self.assertNotContains(
            response, reverse("admin:admin_logentry_changelist"))

    def test_team_members_target_is_publicly_reachable(self):
        # The link opens in a new tab for any staff user, so it must not be
        # gated behind a login the editor/contributor accounts may not pass.
        response = self.client.get(reverse("website:view_project_people"))
        self.assertEqual(response.status_code, 200)
