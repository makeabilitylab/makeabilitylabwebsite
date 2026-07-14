"""
Regression tests for the log-path degradation guard added in issue #1283.

The base ``LOGGING`` config used to hardcode ``/code/media/debug.log``. Because
Django evaluates ``LOGGING`` at ``django.setup()``, any host missing that exact
directory (e.g. GitHub Actions CI) crashed with ``FileNotFoundError`` before a
single request or test ran. The fix derives the path from ``BASE_DIR`` and, if
the log directory can't be created or written, degrades the file handler to a
``NullHandler`` so startup never dies. These tests pin that helper's behavior.

Pure logic, no DB — a fast ``SimpleTestCase``.
"""

import shutil
import tempfile

from django.test import SimpleTestCase

from makeabilitylab.settings import _log_dir_is_writable


class LogDirWritabilityTests(SimpleTestCase):
    def test_writable_dir_returns_true(self):
        """A normal, writable directory keeps the file handler active."""
        tmp = tempfile.mkdtemp()
        try:
            self.assertTrue(_log_dir_is_writable(tmp))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_uncreatable_dir_returns_false(self):
        """A dir that can't be created degrades to False (→ NullHandler).

        ``/dev/null`` is a file on every POSIX host, so ``os.makedirs`` under it
        raises ``NotADirectoryError`` (an ``OSError``) — the helper must swallow
        it and report the directory as unusable rather than letting the error
        propagate into ``django.setup()``.
        """
        self.assertFalse(_log_dir_is_writable('/dev/null/cannot/create'))
