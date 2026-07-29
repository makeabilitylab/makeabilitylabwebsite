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

import logging
import logging.config
import os
import shutil
import tempfile
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, override_settings

from makeabilitylab.settings import (
    _ensure_log_dir_writable,
    _file_log_handler,
    _lock_file_directory,
)
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
    """Both branches of the builder behind ``LOGGING['handlers']['file']``.

    The enabled branch must build a *multiprocess-safe* rotating handler
    (issue #1439): Gunicorn's 3 workers share one debug.log, and the stdlib
    ``RotatingFileHandler`` races on rollover across processes — workers rename
    each other's freshly rotated files and records are silently lost.
    """

    def test_enabled_builds_concurrent_rotating_file_handler(self):
        handler = _file_log_handler("/tmp/probe/debug.log", "INFO", True)
        self.assertEqual(
            handler["class"], "concurrent_log_handler.ConcurrentRotatingFileHandler"
        )
        self.assertEqual(handler["filename"], "/tmp/probe/debug.log")
        self.assertEqual(handler["level"], "INFO")
        self.assertEqual(handler["formatter"], "verbose")

    def test_missing_package_degrades_to_stdlib_rotating_handler(self):
        """An unimportable handler class must not abort ``django.setup()``.

        ``dictConfig`` raises ValueError on a class it can't resolve, and that
        propagates out of ``django.setup()`` — no NullHandler degrade, no
        /version.json, no admin callout. The container runs the bind-mounted
        checkout against whatever site-packages the image was last built with,
        so "settings.py is ahead of the installed packages" is a real state
        (branch switch without --build; the gap between the deploy webhook's
        git pull and its image build). Degrade to the racy-but-working stdlib
        handler instead.
        """
        with mock.patch("makeabilitylab.settings._HAS_CONCURRENT_LOG_HANDLER", False):
            handler = _file_log_handler("/tmp/probe/debug.log", "INFO", True)
        self.assertEqual(handler["class"], "logging.handlers.RotatingFileHandler")
        # The kwarg is a concurrent-log-handler extension; passing it to the
        # stdlib handler would be a TypeError at dictConfig time.
        self.assertNotIn("lock_file_directory", handler)
        self.assertEqual(handler["maxBytes"], 1024 * 1024 * 5)
        self.assertEqual(handler["backupCount"], 6)

    def test_unusable_lock_dir_degrades_to_stdlib_rotating_handler(self):
        """No usable lock dir → degrade rather than fail silently at emit().

        The concurrent handler reports lock failures through ``handleError``
        (stderr, which nothing reads on the servers) while ``log_to_file``
        would still say healthy — so decide up front, where we can report it.
        """
        with mock.patch("makeabilitylab.settings._lock_file_directory", return_value=None):
            handler = _file_log_handler("/tmp/probe/debug.log", "INFO", True)
        self.assertEqual(handler["class"], "logging.handlers.RotatingFileHandler")
        self.assertNotIn("lock_file_directory", handler)

    def test_lock_dir_is_namespaced_by_uid(self):
        """Processes must not share a lock file across users.

        The lock name comes from the log's basename alone, so a bare temp dir
        gives every process ``/tmp/.__debug.lock`` — opened ``"r+"``. A
        root-owned one (the devcontainer connects as root) locks out the
        ``apache`` workers permanently, since /tmp's sticky bit stops them
        unlinking it. A per-uid directory keeps the lock shared exactly where
        it must be (same-uid Gunicorn workers) and nowhere else.
        """
        lock_dir = _lock_file_directory()
        self.assertIsNotNone(lock_dir)
        self.assertNotEqual(
            os.path.normpath(lock_dir), os.path.normpath(tempfile.gettempdir())
        )
        self.assertTrue(os.path.basename(lock_dir).endswith(str(os.getuid())))

    def test_lock_file_stays_out_of_media_root(self):
        """The handler's lock file must not land in the web-served media tree.

        By default concurrent-log-handler drops its lock file next to the log,
        and LOG_FILE lives inside MEDIA_ROOT (everything under it is publicly
        downloadable). The config must redirect lock files elsewhere.
        """
        handler = _file_log_handler(settings.LOG_FILE, "INFO", True)
        lock_dir = handler["lock_file_directory"]
        media_root = os.path.join(os.path.normpath(settings.MEDIA_ROOT), "")
        self.assertFalse(
            os.path.normpath(lock_dir).startswith(media_root)
            or os.path.normpath(lock_dir) == os.path.normpath(settings.MEDIA_ROOT),
            f"lock_file_directory {lock_dir!r} is inside MEDIA_ROOT",
        )

    def test_enabled_handler_config_is_instantiable(self):
        """``dictConfig`` must be able to build and use the real handler.

        Guards the class path and constructor kwargs against package changes
        (e.g. ``lock_file_directory`` is a concurrent-log-handler extension —
        a typo'd kwarg here would crash ``django.setup()`` on every server).
        Writes one record and checks it landed, and that no lock file was
        dropped next to the log.

        Note the ``dictConfig`` below is destructive: a non-incremental config
        runs ``logging.config._clearExistingHandlers()``, which closes and
        unregisters *every* handler Django set up, for the rest of the test
        process. The ``finally`` block re-applies ``settings.LOGGING`` so this
        test can't quietly break whichever test runs after it.
        """
        tmp = tempfile.mkdtemp()
        log_file = os.path.join(tmp, "debug.log")
        logger_name = "probe1439"
        try:
            handler_cfg = _file_log_handler(log_file, "INFO", True)
            # 'formatter' refers to LOGGING['formatters'] by name; this minimal
            # config has none, so drop it (dictConfig would fail the lookup).
            handler_cfg.pop("formatter")
            logging.config.dictConfig({
                "version": 1,
                "disable_existing_loggers": False,
                "handlers": {"probe1439_file": handler_cfg},
                "loggers": {
                    logger_name: {"handlers": ["probe1439_file"], "level": "INFO"},
                },
            })
            logging.getLogger(logger_name).info("probe record")
            with open(log_file) as f:
                self.assertIn("probe record", f.read())
            self.assertEqual(os.listdir(tmp), ["debug.log"])
        finally:
            # Detach and close the handler so the temp dir can be removed and
            # no stray handler outlives this test in global logging state.
            probe_logger = logging.getLogger(logger_name)
            for h in list(probe_logger.handlers):
                probe_logger.removeHandler(h)
                h.close()
            # Rebuild the handlers the probe config tore down (see docstring).
            logging.config.dictConfig(settings.LOGGING)
            shutil.rmtree(tmp, ignore_errors=True)

    def test_disabled_degrades_to_nullhandler(self):
        handler = _file_log_handler("/tmp/probe/debug.log", "INFO", False)
        self.assertEqual(handler, {"class": "logging.NullHandler"})
        # No filename key at all -- nothing for logging.config to try to open.
        self.assertNotIn("filename", handler)


class LogFileLocationTests(SimpleTestCase):
    def test_default_log_file_is_under_media_root(self):
        """The log must live inside MEDIA_ROOT or it becomes unreadable.

        ``LOG_DIR`` and ``MEDIA_ROOT`` are computed independently in settings.py
        (LOGGING has to be built before MEDIA_ROOT is defined), so this pins them
        together: media/ is the tree bind-mounted to the shared CSE filesystem, and
        SSH to that filesystem is the *only* way to read debug.log on -test and prod
        (there is no shell on those hosts, and the old /logs/ URL is gone). A log
        written outside it is a log nobody can read. Skipped when ``ML_LOG_DIR`` is
        set, since an explicit override may point elsewhere.
        """
        if os.environ.get("ML_LOG_DIR"):
            self.skipTest("ML_LOG_DIR override in effect")
        self.assertEqual(
            settings.LOG_FILE, os.path.join(settings.MEDIA_ROOT, "debug.log")
        )


class LogRotationSettingTests(SimpleTestCase):
    """``LOG_ROTATION`` is what /version.json reports as ``log_rotation``.

    It's derived from the built ``LOGGING`` dict so the reported handler can't
    drift from the configured one — including in ``settings_test``, which swaps
    the file handler for a NullHandler and must keep the two in step.
    """

    def test_log_rotation_names_the_configured_handler_class(self):
        self.assertEqual(
            settings.LOG_ROTATION,
            settings.LOGGING["handlers"]["file"]["class"].rsplit(".", 1)[-1],
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
