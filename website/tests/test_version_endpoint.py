"""Tests for the machine-readable version / build-info endpoint (#1366).

``/version/`` (and ``/version.json``) returns JSON describing the running build
so we can confirm what code a server is actually deploying without scraping the
HTML comment in ``base.html``. These pin:
  - routing of both URLs to the same view,
  - the JSON shape and that version/description/environment come from settings,
  - ``Cache-Control: no-store`` (so a proxy can't serve a stale version),
  - that git_sha/built_at are read from the entrypoint-written build-info file,
    and fall back to ``"unknown"`` when the file is absent (e.g. local dev),
  - that log_to_file/log_file report logging health (#1283) -- with no console
    access on -test or prod, this endpoint is how we confirm a deployed server
    is actually writing logs rather than silently discarding them.
"""

import json
import os

from django.test import SimpleTestCase, override_settings
from django.urls import resolve, reverse

import importlib

# Import the submodule (not the re-exported `version` function, which shadows the
# `website.views.version` name in the package namespace) so we can read/patch its
# module-level BUILD_INFO_PATH.
version_module = importlib.import_module("website.views.version")


class VersionRoutingTests(SimpleTestCase):
    def test_version_url_resolves(self):
        match = resolve("/version/")
        self.assertEqual(match.url_name, "version")
        self.assertIs(match.func, version_module.version)

    def test_version_json_url_resolves_to_same_view(self):
        match = resolve("/version.json")
        self.assertIs(match.func, version_module.version)

    def test_reverse(self):
        self.assertEqual(reverse("website:version"), "/version/")


@override_settings(
    ML_WEBSITE_VERSION="9.9.9",
    ML_WEBSITE_VERSION_DESCRIPTION="Test description.",
    DJANGO_ENV="TEST",
)
class VersionResponseTests(SimpleTestCase):
    def test_payload_from_settings_and_no_store_header(self):
        response = self.client.get("/version/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(response["Cache-Control"], "no-store")
        data = json.loads(response.content)
        self.assertEqual(data["version"], "9.9.9")
        self.assertEqual(data["description"], "Test description.")
        self.assertEqual(data["environment"], "TEST")
        # Always present, even without a build-info file.
        self.assertIn("git_sha", data)
        self.assertIn("built_at", data)
        # The live WSGI server's self-reported SERVER_SOFTWARE (#1034); always
        # present so we can confirm gunicorn vs. the dev runserver in deploys.
        self.assertIn("server", data)
        # Logging health (#1283) -- always present so a deploy check can assert on it.
        self.assertIn("log_to_file", data)
        self.assertIn("log_file", data)
        # Which rotation handler is live (#1439) -- the only remote way to see
        # that the multiprocess-safe handler degraded.
        self.assertIn("log_rotation", data)

    def test_server_reflects_wsgi_server_software(self):
        # The view reports request.META["SERVER_SOFTWARE"] verbatim; on the real
        # servers that's "gunicorn/<ver>" after #1034. Simulate it here.
        data = json.loads(
            self.client.get("/version/", SERVER_SOFTWARE="gunicorn/23.0.0").content
        )
        self.assertEqual(data["server"], "gunicorn/23.0.0")

    @override_settings(LOG_TO_FILE=True, LOG_FILE="/code/media/debug.log")
    def test_reports_healthy_logging(self):
        data = json.loads(self.client.get("/version/").content)
        self.assertTrue(data["log_to_file"])
        self.assertEqual(data["log_file"], "/code/media/debug.log")

    @override_settings(LOG_TO_FILE=False, LOG_FILE="/nope/debug.log")
    def test_reports_degraded_logging(self):
        """``log_to_file: false`` is the remote signal that a server is logging
        nowhere (#1283); ``log_file`` names the directory that failed."""
        data = json.loads(self.client.get("/version/").content)
        self.assertFalse(data["log_to_file"])
        self.assertEqual(data["log_file"], "/nope/debug.log")

    @override_settings(LOG_ROTATION="RotatingFileHandler")
    def test_reports_degraded_rotation(self):
        """Anything but ``ConcurrentRotatingFileHandler`` means Gunicorn's three
        workers can race on rollover again (#1439) -- invisible otherwise, since
        there's no console on -test or prod."""
        data = json.loads(self.client.get("/version/").content)
        self.assertEqual(data["log_rotation"], "RotatingFileHandler")

    def test_build_info_missing_falls_back_to_unknown(self):
        with override_settings():
            # Point at a path that doesn't exist.
            original = version_module.BUILD_INFO_PATH
            version_module.BUILD_INFO_PATH = "/nonexistent/build-info.json"
            try:
                data = json.loads(self.client.get("/version/").content)
            finally:
                version_module.BUILD_INFO_PATH = original
        self.assertEqual(data["git_sha"], "unknown")
        self.assertEqual(data["built_at"], "unknown")

    def test_build_info_read_from_file(self):
        path = os.path.join(
            os.path.dirname(__file__), "__version_build_info_probe.json"
        )
        with open(path, "w") as f:
            json.dump({"git_sha": "abc1234", "built_at": "2026-06-21T18:30:00-07:00"}, f)
        original = version_module.BUILD_INFO_PATH
        version_module.BUILD_INFO_PATH = path
        try:
            data = json.loads(self.client.get("/version/").content)
        finally:
            version_module.BUILD_INFO_PATH = original
            os.remove(path)
        self.assertEqual(data["git_sha"], "abc1234")
        self.assertEqual(data["built_at"], "2026-06-21T18:30:00-07:00")
