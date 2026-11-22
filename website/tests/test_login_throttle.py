"""Admin login throttling (django-axes), configured in settings.py.

Policy under test: repeated wrong passwords lock the *username* (not the IP
address) for a cool-off period, a locked username is refused even with the
right password, and other usernames are unaffected.

The suite runs with ``AXES_ENABLED = False`` (see settings_test.py); these tests
switch it back on, with a small limit so they stay fast.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
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
