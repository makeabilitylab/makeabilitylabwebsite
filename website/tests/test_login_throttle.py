"""Admin login throttling (django-axes), configured in settings.py.

Policy under test: repeated wrong passwords lock the *username* (not the IP
address) for a cool-off period, a locked username is refused even with the
right password, and other usernames are unaffected.

The suite runs with ``AXES_ENABLED = False`` (see settings_test.py); these tests
switch it back on, with a small limit so they stay fast.
"""
from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from axes.utils import reset

PASSWORD = "correct-horse-battery-staple"


@override_settings(AXES_ENABLED=True, AXES_FAILURE_LIMIT=3)
class AdminLoginThrottleTests(TestCase):

    def setUp(self):
        User = get_user_model()
        self.alice = User.objects.create_superuser("alice", "", PASSWORD)
        self.bob = User.objects.create_superuser("bob", "", PASSWORD)
        self.login_url = reverse("admin:login")
        reset()  # no lockout state carried in from another test
        self.addCleanup(reset)

    def attempt(self, username, password):
        """POST the admin login form and return the response."""
        return self.client.post(
            self.login_url,
            {"username": username, "password": password, "next": "/admin/"},
        )

    def test_correct_password_still_logs_in(self):
        response = self.attempt("alice", PASSWORD)
        self.assertEqual(response.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)

    def test_username_locks_after_limit_even_with_right_password(self):
        for _ in range(3):
            self.attempt("alice", "wrong")
        response = self.attempt("alice", PASSWORD)
        self.assertEqual(response.status_code, 429)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_below_limit_does_not_lock(self):
        for _ in range(2):
            self.assertEqual(self.attempt("alice", "wrong").status_code, 200)
        self.assertEqual(self.attempt("alice", PASSWORD).status_code, 302)

    def test_success_resets_the_failure_count(self):
        for _ in range(2):
            self.attempt("alice", "wrong")
        self.attempt("alice", PASSWORD)
        self.client.logout()
        # Two more failures: would be 4 in a row without the reset.
        for _ in range(2):
            self.attempt("alice", "wrong")
        self.assertEqual(self.attempt("alice", PASSWORD).status_code, 302)

    def test_lock_is_per_username_not_per_client(self):
        """Locking alice must not lock bob, though both come from one client IP."""
        for _ in range(3):
            self.attempt("alice", "wrong")
        self.assertEqual(self.attempt("alice", PASSWORD).status_code, 429)
        self.assertEqual(self.attempt("bob", PASSWORD).status_code, 302)

    def test_unknown_usernames_are_counted_too(self):
        """Guessing at a name that does not exist is throttled the same way."""
        for _ in range(3):
            self.attempt("nobody", "wrong")
        self.assertEqual(self.attempt("nobody", "wrong").status_code, 429)

    def test_unknown_usernames_are_never_stored_in_plain_text(self):
        """A password typed into the username box must never reach the database."""
        from axes.models import AccessAttempt, AccessFailureLog
        from website.utils.login_throttle import UNKNOWN_PREFIX

        self.attempt("MySecretPassw0rd!", "whatever")
        self.attempt("root", "whatever")
        for model in (AccessAttempt, AccessFailureLog):
            names = set(model.objects.values_list("username", flat=True))
            self.assertEqual(len(names), 2, model.__name__)  # one counter per name
            for name in names:
                self.assertTrue(name.startswith(UNKNOWN_PREFIX), name)
                self.assertNotIn("MySecret", name)
                self.assertNotIn("root", name)

    def test_unknown_and_real_names_are_indistinguishable(self):
        """Locking some made-up names must not reveal which other names exist.

        If unknown names shared one counter, a fresh made-up name would get 429
        here while a real one got 200.
        """
        for name in ("root", "admin", "test"):
            for _ in range(3):
                self.attempt(name, "wrong")
        self.assertEqual(self.attempt("root", "wrong").status_code, 429)
        made_up = self.attempt("doesnotexist", "wrong").status_code
        real = self.attempt("alice", "wrong").status_code
        self.assertEqual(made_up, real)
        self.assertEqual(real, 200)
        # And a mistyped username does not lock the real account.
        self.assertEqual(self.attempt("alice", PASSWORD).status_code, 302)

    @override_settings(AXES_ENABLED=False)
    def test_off_switch_really_stops_the_lockout(self):
        from axes.models import AccessAttempt

        for _ in range(6):
            self.attempt("alice", "wrong")
        self.assertEqual(self.attempt("alice", PASSWORD).status_code, 302)
        self.assertEqual(AccessAttempt.objects.count(), 0)

    def test_dashboard_warning_is_for_superusers_only(self):
        from django.core.management import call_command
        from django.contrib.auth.models import Group

        call_command("setup_admin_groups", verbosity=0)
        editor = get_user_model().objects.create_user("erin", "", PASSWORD, is_staff=True)
        editor.groups.add(Group.objects.get(name="Editors"))
        marker = "admin login throttling is"
        for user, state, shown in ((self.bob, "off: test", True),
                                   (self.bob, "on", False),
                                   (editor, "off: test", False)):
            client = Client()
            client.force_login(user)
            with override_settings(LOGIN_THROTTLE=state):
                response = client.get(reverse("admin:index"))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(marker in response.content.decode(), shown, (user.username, state))

    def test_failed_logins_are_recorded(self):
        from axes.models import AccessFailureLog

        self.attempt("alice", "wrong")
        self.assertEqual(AccessFailureLog.objects.filter(username="alice").count(), 1)

    def test_lockout_page(self):
        for _ in range(3):
            self.attempt("alice", "wrong")
        response = self.attempt("alice", PASSWORD)
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response["Retry-After"], "1800")
        self.assertTemplateUsed(response, "admin/login_locked_out.html")
        self.assertContains(response, '<html lang="en">', status_code=429)
        self.assertContains(response, "within 30 minutes", status_code=429)
        self.assertNotContains(response, PASSWORD, status_code=429)

    def test_signed_in_superuser_can_unlock_by_deleting_rows(self):
        """The documented unlock path: delete the rows under Access attempts."""
        from axes.models import AccessAttempt

        for _ in range(3):
            self.attempt("alice", "wrong")
        self.assertEqual(self.attempt("alice", PASSWORD).status_code, 429)

        admin_client = Client()
        admin_client.force_login(self.bob)
        changelist = reverse("admin:axes_accessattempt_changelist")
        ids = list(AccessAttempt.objects.values_list("pk", flat=True))
        response = admin_client.post(changelist, {
            "action": "delete_selected", "_selected_action": ids, "post": "yes"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.attempt("alice", PASSWORD).status_code, 302)

    def test_axes_admin_is_superuser_only(self):
        """Editors must not see login records (IP addresses, usernames)."""
        from django.core.management import call_command
        from django.contrib.auth.models import Group

        call_command("setup_admin_groups", verbosity=0)
        editor = get_user_model().objects.create_user("erin", "", PASSWORD, is_staff=True)
        editor.groups.add(Group.objects.get(name="Editors"))
        editor_client = Client()
        editor_client.force_login(editor)
        for model in ("accessattempt", "accesslog", "accessfailurelog"):
            url = reverse(f"admin:axes_{model}_changelist")
            self.assertEqual(editor_client.get(url).status_code, 403, model)


class AxesChangelistHelpTests(TestCase):
    """Each axes changelist explains what it records (templates/admin/axes/change_list.html)."""

    PAGES = {
        "accessattempt": "To unlock someone now,",
        "accesslog": "Every successful sign-in",
        "accessfailurelog": "Every wrong password",
    }

    def setUp(self):
        user = get_user_model().objects.create_superuser("alice", "", PASSWORD)
        self.client.force_login(user)

    def test_each_page_has_its_own_explanation(self):
        for model, own_text in self.PAGES.items():
            with self.subTest(model=model):
                response = self.client.get(reverse(f"admin:axes_{model}_changelist"))
                self.assertContains(response, 'class="ml-axes-help"')
                self.assertContains(response, own_text)
                for other, other_text in self.PAGES.items():
                    if other != model:
                        self.assertNotContains(response, other_text)

    def test_numbers_in_the_text_match_the_settings(self):
        """The template hard-codes them; fail here rather than show stale numbers."""
        from datetime import timedelta
        from django.conf import settings

        self.assertEqual(settings.AXES_FAILURE_LIMIT, 10)  # "Ten in a row"
        self.assertEqual(settings.AXES_COOLOFF_TIME, timedelta(minutes=30))
        self.assertEqual(settings.AXES_ACCESS_FAILURE_LOG_PER_USER_LIMIT, 1000)


class ThrottleConfigTests(TestCase):
    """Pin the production policy so a settings edit can't quietly weaken it."""

    def test_policy(self):
        from datetime import timedelta
        from django.conf import settings

        self.assertEqual(settings.AXES_LOCKOUT_PARAMETERS, ["username"])
        self.assertLessEqual(settings.AXES_FAILURE_LIMIT, 10)
        self.assertGreaterEqual(settings.AXES_COOLOFF_TIME, timedelta(minutes=15))
        # Further guesses during a lockout must not extend it indefinitely.
        self.assertFalse(settings.AXES_RESET_COOL_OFF_ON_FAILURE_DURING_LOCKOUT)
        self.assertEqual(
            settings.AUTHENTICATION_BACKENDS[0], "axes.backends.AxesStandaloneBackend")
        self.assertEqual(settings.MIDDLEWARE[-1], "axes.middleware.AxesMiddleware")
        self.assertIn("axes", settings.INSTALLED_APPS)
        self.assertTrue(settings.AXES_ENABLE_ACCESS_FAILURE_LOG)


class ThrottleSwitchTests(SimpleTestCase):
    """settings.py decides on/off at import time; load it fresh in a subprocess."""

    def load(self, extra_env=None, hide_axes=False):
        """Import settings in a clean interpreter and return what it decided."""
        import json, os, subprocess, sys
        code = (
            "import sys, json\n"
            + ("sys.modules['axes'] = None\n"
               "import importlib.util as u\n"
               "_f = u.find_spec\n"
               "u.find_spec = lambda n, *a, **k: None if n == 'axes' else _f(n, *a, **k)\n"
               if hide_axes else "")
            + "from makeabilitylab import settings as s\n"
            "print(json.dumps({'throttle': s.LOGIN_THROTTLE, 'enabled': s.AXES_ENABLED,\n"
            "  'app': 'axes' in s.INSTALLED_APPS,\n"
            "  'mw': 'axes.middleware.AxesMiddleware' in s.MIDDLEWARE,\n"
            "  'backends': getattr(s, 'AUTHENTICATION_BACKENDS', None)}))\n"
        )
        env = {k: v for k, v in os.environ.items()
               if k not in ("DJANGO_ENV", "ML_DISABLE_LOGIN_THROTTLE", "DJANGO_SETTINGS_MODULE")}
        env.update(extra_env or {})
        from django.conf import settings
        out = subprocess.run([sys.executable, "-c", code], cwd=settings.BASE_DIR,
                             env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])
        return json.loads(out.stdout.strip().splitlines()[-1])

    def test_on_by_default(self):
        result = self.load()
        self.assertEqual(result["throttle"], "on")
        self.assertTrue(result["enabled"] and result["app"] and result["mw"])

    def test_environment_switch_turns_it_off(self):
        result = self.load({"ML_DISABLE_LOGIN_THROTTLE": "true"})
        self.assertFalse(result["enabled"])
        self.assertTrue(result["throttle"].startswith("off"))

    def test_empty_or_other_values_leave_it_on(self):
        for value in ("", "false", "0"):
            self.assertTrue(self.load({"ML_DISABLE_LOGIN_THROTTLE": value})["enabled"], value)

    def test_common_truthy_spellings_also_turn_it_off(self):
        """In an emergency nobody should be defeated by typing 1 instead of true."""
        for value in ("TRUE", "1", " yes "):
            self.assertFalse(self.load({"ML_DISABLE_LOGIN_THROTTLE": value})["enabled"], value)

    def test_settings_still_load_when_the_package_is_missing(self):
        """Mid-deploy the old image runs the new settings; workers must boot."""
        result = self.load(hide_axes=True)
        self.assertFalse(result["app"] or result["mw"])
        self.assertIsNone(result["backends"])
        self.assertTrue(result["throttle"].startswith("off"))
