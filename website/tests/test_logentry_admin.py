"""
Regression tests for the read-only LogEntry admin (site-wide action log).

Pins the two properties that matter: (1) the LogEntry changelist is a
read-only viewer—no add/change/delete—and (2) it is superuser-only, so
editors/contributors can neither see nor reach it. See website/admin/
logentry_admin.py.
"""

from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from website.admin.admin_site import ml_admin_site
from website.admin.logentry_admin import LogEntryAdmin
from website.tests.base import DatabaseTestCase

User = get_user_model()


class LogEntryAdminPermissionTests(DatabaseTestCase):
    """The audit log is read-only and superuser-only."""

    def setUp(self):
        self.admin = LogEntryAdmin(LogEntry, ml_admin_site)
        self.superuser = User.objects.create_superuser(
            username="root", email="root@example.com", password="pw")
        self.editor = User.objects.create_user(
            username="editor", email="editor@example.com", password="pw",
            is_staff=True)

    def _request(self, user):
        # Lightweight stand-in: the permission hooks only read request.user.
        class _Req:
            pass
        req = _Req()
        req.user = user
        return req

    def test_log_is_read_only(self):
        req = self._request(self.superuser)
        self.assertFalse(self.admin.has_add_permission(req))
        self.assertFalse(self.admin.has_change_permission(req))
        self.assertFalse(self.admin.has_delete_permission(req))

    def test_only_superusers_can_view(self):
        self.assertTrue(
            self.admin.has_view_permission(self._request(self.superuser)))
        self.assertTrue(
            self.admin.has_module_permission(self._request(self.superuser)))
        self.assertFalse(
            self.admin.has_view_permission(self._request(self.editor)))
        self.assertFalse(
            self.admin.has_module_permission(self._request(self.editor)))


class LogEntryAdminViewTests(DatabaseTestCase):
    """End-to-end: the changelist renders for superusers and is blocked otherwise."""

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="root", email="root@example.com", password="pw")
        self.editor = User.objects.create_user(
            username="editor", email="editor@example.com", password="pw",
            is_staff=True)
        # Seed one log row of each action type so the display columns render.
        ct = ContentType.objects.get_for_model(User)
        for flag in (ADDITION, CHANGE, DELETION):
            LogEntry.objects.log_action(
                user_id=self.superuser.pk,
                content_type_id=ct.pk,
                object_id=self.editor.pk,
                object_repr=str(self.editor),
                action_flag=flag,
                change_message="test",
            )

    def test_superuser_sees_changelist(self):
        self.client.force_login(self.superuser)
        url = reverse("admin:admin_logentry_changelist")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        # The seeded rows' object_repr should appear in the rendered list.
        self.assertContains(resp, str(self.editor))

    def test_non_superuser_is_denied(self):
        self.client.force_login(self.editor)
        url = reverse("admin:admin_logentry_changelist")
        resp = self.client.get(url)
        # Django admin redirects/403s when module perms are absent; either way
        # the editor must not get a 200 list of everyone's actions.
        self.assertNotEqual(resp.status_code, 200)


class LogEntryAdminDisplayTests(DatabaseTestCase):
    """The custom display columns don't raise on any action type."""

    def setUp(self):
        self.admin = LogEntryAdmin(LogEntry, ml_admin_site)
        self.user = User.objects.create_superuser(
            username="root", email="root@example.com", password="pw")
        self.ct = ContentType.objects.get_for_model(User)

    def _entry(self, flag):
        return LogEntry.objects.log_action(
            user_id=self.user.pk, content_type_id=self.ct.pk,
            object_id=self.user.pk, object_repr=str(self.user),
            action_flag=flag, change_message="changed something")

    def test_deletion_object_link_falls_back_to_repr(self):
        # Deletions have no live object to link to; must fall back to text,
        # never raise (get_admin_url would point at a possibly-gone row).
        entry = self._entry(DELETION)
        self.assertIn(str(self.user), self.admin.object_link(entry))

    def test_action_label_covers_all_flags(self):
        for flag, expected in ((ADDITION, "Added"),
                               (CHANGE, "Changed"),
                               (DELETION, "Deleted")):
            self.assertIn(expected, self.admin.action_label(self._entry(flag)))
