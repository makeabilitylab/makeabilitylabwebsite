"""
Regression tests for the log-path degradation guard added in issue #1283.

The base ``LOGGING`` config used to hardcode ``/code/media/debug.log``. Because
Django evaluates ``LOGGING`` at ``django.setup()``, any host missing that exact
directory (e.g. GitHub Actions CI) crashed with ``FileNotFoundError`` before a
single request or test ran. The fix derives the path from ``BASE_DIR`` and, if
the log directory can't be created or written, degrades the file handler to a
``NullHandler`` so startup never dies.

Degrading silently is its own hazard: the ``django`` logger has only the ``file``
handler and the ``website`` logger's console handler is gated by
``require_debug_true``, so on a server an unwritable log dir means no logs at all
-- and we have no console access on -test or prod. The degraded state is
therefore surfaced on ``/version.json`` and on the admin dashboard; both are
pinned here and in ``test_version_endpoint.py``.

Note that ``settings_test.py`` replaces ``LOGGING['handlers']['file']`` with a
``NullHandler`` before any test runs, so the live ``LOGGING`` dict can't be used
to exercise the degrade branch. That's why ``settings.py`` factors the handler
construction into ``_file_log_handler`` -- these tests call it directly.

Mostly pure logic; the admin-dashboard tests need the DB for a superuser login.
"""

import os
import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, override_settings

from makeabilitylab.settings import _ensure_log_dir_writable, _file_log_handler
from website.tests.base import DatabaseTestCase


class LogDirWritabilityTests(SimpleTestCase):
    def test_writable_dir_returns_true(self):
        """A normal, writable directory keeps the file handler active."""
        tmp = tempfile.mkdtemp()
        try:
            self.assertTrue(_ensure_log_dir_writable(tmp))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_missing_dir_is_created(self):
        """The helper creates the directory rather than just inspecting it."""
        tmp = tempfile.mkdtemp()
        target = os.path.join(tmp, "nested", "logs")
        try:
            self.assertTrue(_ensure_log_dir_writable(target))
            self.assertTrue(os.path.isdir(target))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_uncreatable_dir_returns_false(self):
        """A dir that can't be created degrades to False (→ NullHandler).

        ``/dev/null`` is a file on every POSIX host, so ``os.makedirs`` under it
        raises ``NotADirectoryError`` (an ``OSError``) — the helper must swallow
        it and report the directory as unusable rather than letting the error
        propagate into ``django.setup()``.

        Deliberately not tested: an existing-but-unwritable dir (``chmod 0o500``).
        ``os.access`` returns True for root regardless of mode, so such a test
        would pass locally and fail in the root devcontainer.
        """
        self.assertFalse(_ensure_log_dir_writable("/dev/null/cannot/create"))


class FileLogHandlerTests(SimpleTestCase):
    """Both branches of the builder behind ``LOGGING['handlers']['file']``."""

    def test_enabled_builds_rotating_file_handler(self):
        handler = _file_log_handler("/tmp/probe/debug.log", "INFO", True)
        self.assertEqual(handler["class"], "logging.handlers.RotatingFileHandler")
        self.assertEqual(handler["filename"], "/tmp/probe/debug.log")
        self.assertEqual(handler["level"], "INFO")
        self.assertEqual(handler["formatter"], "verbose")

    def test_disabled_degrades_to_nullhandler(self):
        handler = _file_log_handler("/tmp/probe/debug.log", "INFO", False)
        self.assertEqual(handler, {"class": "logging.NullHandler"})
        # No filename key at all -- nothing for logging.config to try to open.
        self.assertNotIn("filename", handler)


class LogFileLocationTests(SimpleTestCase):
    def test_default_log_file_is_under_media_root(self):
        """The log must live inside MEDIA_ROOT or the /logs/ URL breaks.

        ``LOG_DIR`` and ``MEDIA_ROOT`` are computed independently in settings.py
        (LOGGING has to be built before MEDIA_ROOT is defined), so this pins them
        together: the web-served ``/logs/debug.log`` on -test and prod works only
        because the log file sits inside the bind-mounted media root. Skipped when
        ``ML_LOG_DIR`` is set, since an explicit override may point elsewhere.
        """
        if os.environ.get("ML_LOG_DIR"):
            self.skipTest("ML_LOG_DIR override in effect")
        self.assertEqual(
            settings.LOG_FILE, os.path.join(settings.MEDIA_ROOT, "debug.log")
        )


class AdminLoggingWarningTests(DatabaseTestCase):
    """The admin dashboard callout that surfaces degraded logging (#1283).

    This callout and the ``/version.json`` field are the only ways to notice a
    logging blackout on -test or prod, where we have no console access.
    """

    def setUp(self):
        super().setUp()
        User = get_user_model()
        self.superuser = User.objects.create_superuser(
            username="logadmin", email="logadmin@example.com", password="pw-for-test"
        )
        self.editor = User.objects.create_user(
            username="logeditor",
            email="logeditor@example.com",
            password="pw-for-test",
            is_staff=True,
        )

    @override_settings(LOG_TO_FILE=False, LOG_FILE="/code/media/debug.log")
    def test_warning_shown_to_superuser_when_logging_degraded(self):
        self.client.force_login(self.superuser)
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "file logging is disabled")
        # The resolved path is what tells you which directory was at fault.
        self.assertContains(response, "/code/media/debug.log")

    @override_settings(LOG_TO_FILE=True)
    def test_no_warning_when_logging_healthy(self):
        self.client.force_login(self.superuser)
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "file logging is disabled")

    @override_settings(LOG_TO_FILE=False)
    def test_warning_hidden_from_non_superusers(self):
        """Only the maintainer can fix a log-dir problem, so don't alarm editors."""
        self.client.force_login(self.editor)
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "file logging is disabled")
