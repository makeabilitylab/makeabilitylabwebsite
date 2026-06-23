"""
Regression tests for the setup_admin_groups management command (#1125).

Two layers:

1. SetupAdminGroupsTests pins the *exact* permission sets of the Editors and
   Contributors groups so a future model rename/removal, or an accidental edit
   to the spec, can't silently widen or drop a group's access. They also assert
   the design's security boundaries: neither group can manage users/groups
   (account admin stays superuser-only), nor touch Grant or Award (admin-only).

2. SetupAdminGroupsSafetyTests + DockerEntrypointWiringTests cover the
   anti-lockout invariants. The command runs on EVERY container start, so it
   must never touch user accounts, the superuser flag, login flags
   (is_staff/is_active), or group membership — only the two groups' permission
   lists. And a superuser must keep full access no matter how the groups are
   configured, so the maintainer can always log in and repair things.

The command builds permissions from ContentType + Permission rows, which Django
auto-creates during test-DB setup, so these run on the standard DatabaseTestCase.
"""

from pathlib import Path

from django.contrib.auth.models import Group, Permission, User
from django.core.management import call_command

from website.tests.base import DatabaseTestCase

REPO_ROOT = Path(__file__).resolve().parents[2]


def _codenames(group_name):
    """Return the set of 'app_label.codename' strings granted to a group."""
    group = Group.objects.get(name=group_name)
    return {
        f"{p.content_type.app_label}.{p.codename}"
        for p in group.permissions.select_related("content_type")
    }


# The full content set Editors manage, each with all four CRUD actions.
EDITORS_MODELS = [
    "banner", "person", "position", "project", "keyword", "talk",
    "publication", "poster", "news", "video",
    "photo", "projectumbrella", "sponsor", "projectrole",
]
EXPECTED_EDITORS = {
    f"website.{action}_{model}"
    for model in EDITORS_MODELS
    for action in ("add", "change", "delete", "view")
}

EXPECTED_CONTRIBUTORS = {
    "website.add_person", "website.change_person", "website.view_person",
    "website.add_publication", "website.view_publication",
    "website.add_talk", "website.view_talk",
    "website.add_poster", "website.view_poster",
    "website.add_projectrole", "website.view_projectrole",
}


class SetupAdminGroupsTests(DatabaseTestCase):
    def test_creates_both_groups(self):
        self.assertFalse(Group.objects.filter(name="Editors").exists())
        call_command("setup_admin_groups")
        self.assertTrue(Group.objects.filter(name="Editors").exists())
        self.assertTrue(Group.objects.filter(name="Contributors").exists())

    def test_editors_permission_set_is_exact(self):
        call_command("setup_admin_groups")
        self.assertEqual(_codenames("Editors"), EXPECTED_EDITORS)

    def test_contributors_permission_set_is_exact(self):
        call_command("setup_admin_groups")
        self.assertEqual(_codenames("Contributors"), EXPECTED_CONTRIBUTORS)

    def test_neither_group_can_administer_accounts(self):
        """The escalation boundary: no user/group/permission perms anywhere."""
        call_command("setup_admin_groups")
        for group in ("Editors", "Contributors"):
            for codename in _codenames(group):
                self.assertNotIn("auth.", codename, f"{group} has {codename}")
                self.assertNotIn("logentry", codename, f"{group} has {codename}")

    def test_grant_and_award_are_admin_only(self):
        """Grant (funding) and Award (external recognitions) stay superuser-only."""
        call_command("setup_admin_groups")
        for group in ("Editors", "Contributors"):
            for codename in _codenames(group):
                self.assertNotIn("_grant", codename, f"{group} has {codename}")
                self.assertNotIn("_award", codename, f"{group} has {codename}")

    def test_contributors_cannot_delete_anything(self):
        call_command("setup_admin_groups")
        for codename in _codenames("Contributors"):
            self.assertFalse(
                codename.split(".")[1].startswith("delete_"),
                f"Contributors unexpectedly has delete perm {codename}",
            )

    def test_idempotent_and_self_healing(self):
        """Re-running converges to the same set; a hand-added perm is removed
        and a hand-removed perm is restored (the command is source of truth)."""
        call_command("setup_admin_groups")
        editors = Group.objects.get(name="Editors")

        # Pollute: grant a perm that isn't in the spec, drop one that is.
        stray = Permission.objects.get(codename="delete_grant")
        editors.permissions.add(stray)
        keep = Permission.objects.get(codename="add_publication")
        editors.permissions.remove(keep)

        call_command("setup_admin_groups")

        self.assertEqual(_codenames("Editors"), EXPECTED_EDITORS)


class SetupAdminGroupsSafetyTests(DatabaseTestCase):
    """Anti-lockout invariants: the command must only ever touch the two groups'
    permission lists, never user accounts, login ability, or membership — and a
    superuser must always retain full access."""

    def test_superuser_keeps_full_access_regardless_of_groups(self):
        """A superuser bypasses all permission checks — the ultimate anti-lockout
        guarantee. Even right after the groups are (re)built, the superuser can
        still do the admin-only things no group is granted."""
        boss = User.objects.create_superuser("boss", "boss@example.com", "x")
        call_command("setup_admin_groups")
        boss.refresh_from_db()
        self.assertTrue(boss.is_superuser)
        self.assertTrue(boss.is_staff)
        self.assertTrue(boss.is_active)
        # Implicitly holds every permission, including the withheld ones.
        self.assertTrue(boss.has_perm("auth.add_user"))
        self.assertTrue(boss.has_perm("website.delete_grant"))
        self.assertTrue(boss.has_perm("website.add_award"))

    def test_does_not_create_or_delete_users(self):
        User.objects.create_user("alice")
        before = set(User.objects.values_list("pk", flat=True))
        call_command("setup_admin_groups")
        call_command("setup_admin_groups")  # entrypoint reruns it every boot
        after = set(User.objects.values_list("pk", flat=True))
        self.assertEqual(before, after)

    def test_does_not_change_login_flags(self):
        """Logging into /admin requires is_staff; the command must never flip it
        (or is_active / is_superuser) on anyone."""
        editor = User.objects.create_user("ed", is_staff=True, is_active=True)
        call_command("setup_admin_groups")
        editor.refresh_from_db()
        self.assertTrue(editor.is_staff)
        self.assertTrue(editor.is_active)
        self.assertFalse(editor.is_superuser)

    def test_preserves_group_membership_across_reruns(self):
        """Group membership is assigned in /admin and must survive every deploy —
        the command manages permissions, not who belongs to a group."""
        call_command("setup_admin_groups")
        editor = User.objects.create_user("ed")
        editor.groups.add(Group.objects.get(name="Editors"))

        call_command("setup_admin_groups")  # simulate a redeploy

        editor.refresh_from_db()
        self.assertEqual(
            set(editor.groups.values_list("name", flat=True)), {"Editors"}
        )

    def test_editor_effective_permissions_match_spec(self):
        """Through-the-stack: a non-superuser staff user in Editors actually gets
        exactly the spec's access via has_perm. Re-fetch the user to clear
        Django's per-instance permission cache after the membership change."""
        call_command("setup_admin_groups")
        ed = User.objects.create_user("ed", is_staff=True)
        ed.groups.add(Group.objects.get(name="Editors"))
        ed = User.objects.get(pk=ed.pk)

        self.assertTrue(ed.has_perm("website.change_publication"))
        self.assertTrue(ed.has_perm("website.delete_talk"))
        # ...but not the admin-only or account-admin perms.
        self.assertFalse(ed.has_perm("website.delete_grant"))
        self.assertFalse(ed.has_perm("website.add_award"))
        self.assertFalse(ed.has_perm("auth.add_user"))
        self.assertFalse(ed.has_perm("auth.change_group"))

    def test_contributor_effective_permissions_match_spec(self):
        call_command("setup_admin_groups")
        intern = User.objects.create_user("intern", is_staff=True)
        intern.groups.add(Group.objects.get(name="Contributors"))
        intern = User.objects.get(pk=intern.pk)

        self.assertTrue(intern.has_perm("website.add_publication"))
        self.assertTrue(intern.has_perm("website.view_publication"))
        self.assertTrue(intern.has_perm("website.change_person"))
        # No deletes, no editing others' artifacts, no admin-only, no escalation.
        self.assertFalse(intern.has_perm("website.delete_publication"))
        self.assertFalse(intern.has_perm("website.change_publication"))
        self.assertFalse(intern.has_perm("website.add_grant"))
        self.assertFalse(intern.has_perm("auth.add_user"))

    def test_resilient_to_unknown_model_in_spec(self):
        """A spec entry for a model that doesn't exist (e.g. a future removal,
        like ProjectHeader was) is skipped, not raised — so a stale spec can never
        crash the entrypoint and block the site from booting."""
        from website.management.commands.setup_admin_groups import Command

        perms = Command()._resolve_perms({
            ("website", "ghost_model_that_does_not_exist"): ("add", "change"),
            ("website", "person"): ("add",),
        })
        self.assertEqual({p.codename for p in perms}, {"add_person"})


class DockerEntrypointWiringTests(DatabaseTestCase):
    """Guard the deploy wiring: the command must run on container start, and the
    entrypoint must not 'set -e' before it — otherwise a single failing step would
    abort the boot and lock everyone out of a site that never starts."""

    def _entrypoint(self):
        return (REPO_ROOT / "docker-entrypoint.sh").read_text()

    def test_entrypoint_invokes_setup_admin_groups(self):
        self.assertIn("manage.py setup_admin_groups", self._entrypoint())

    def test_entrypoint_does_not_abort_on_error(self):
        for line in self._entrypoint().splitlines():
            stripped = line.strip()
            self.assertNotEqual(stripped, "set -e")
            self.assertFalse(stripped.startswith("set -e "))
            self.assertFalse(stripped.startswith("set -o errexit"))
            self.assertFalse(stripped.startswith("set -eu"))
