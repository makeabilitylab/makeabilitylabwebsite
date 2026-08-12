"""
Tests for database-backup health reporting (#1443).

The end-to-end proof that a dump actually *restores* lives in
``scripts/test_backup_restore.sh`` and ``scripts/test_backup_restore_django.sh``
(they need Docker, so they can't run in this suite). These tests cover the
Django half: reading the sidecar's status file and reporting it correctly.

The most important behavior pinned here is that a broken or missing status file
degrades to "unknown" instead of raising. This code runs inside
``each_context``, so an exception would take the entire admin down — the exact
opposite of what a backup-health feature should do.

``BackupStatusFileTests``/``BackupWarningSuppressionTests``/``FormatBytesTests``
exercise ``get_backup_status()`` directly. ``AdminBackupWarningTests`` below
goes one layer further and proves the wiring itself -- that
``MakeabilityLabAdminSite.each_context`` actually reaches the rendered
``/admin/`` and Data Health pages -- mirroring ``AdminLoggingWarningTests`` in
``test_logging_config.py`` for the sibling ``LOG_TO_FILE`` feature.
"""

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, override_settings
from django.urls import reverse

from website.tests.base import DatabaseTestCase
from website.utils.backup_status import format_bytes, get_backup_status

NOW = datetime(2026, 8, 7, 12, 0, 0, tzinfo=timezone.utc)


def _iso(dt):
    """Render a datetime the way the sidecar writes them ('...Z')."""
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


def _status_payload(**overrides):
    """A well-formed status.json body, matching what pg_backup.sh writes."""
    payload = {
        'schema_version': 1,
        'database': 'makeability',
        'last_attempt_at': '2026-08-07T03:00:00Z',
        'last_attempt_ok': True,
        'error': None,
        'last_backup_at': '2026-08-07T03:00:00Z',
        'last_backup_file': 'makeability-2026-08-07.sql.gz',
        'last_backup_bytes': 12684,
        'oldest_backup_at': '2026-07-25T03:00:00Z',
        'backup_count': 14,
        'retention_days': 14,
    }
    payload.update(overrides)
    return payload


class BackupStatusFileTests(SimpleTestCase):
    """Reading and interpreting the sidecar's status file."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, 'status.json')

    def _write(self, payload):
        with open(self.path, 'w', encoding='utf-8') as handle:
            if isinstance(payload, str):
                handle.write(payload)
            else:
                json.dump(payload, handle)
        return self.path

    def test_healthy_backup_is_reported_healthy(self):
        self._write(_status_payload())
        status = get_backup_status(status_file=self.path, now=NOW)

        self.assertTrue(status['available'])
        self.assertTrue(status['ok'])
        self.assertTrue(status['healthy'])
        self.assertFalse(status['stale'])
        self.assertFalse(status['should_warn'])
        self.assertIsNone(status['problem'])
        self.assertEqual(status['age_hours'], 9.0)
        self.assertEqual(status['backup_count'], 14)
        self.assertEqual(status['last_backup_file'], 'makeability-2026-08-07.sql.gz')

    @override_settings(BACKUP_STALE_AFTER_HOURS=36)
    def test_backup_older_than_threshold_is_stale(self):
        old = (NOW - timedelta(hours=50)).strftime('%Y-%m-%dT%H:%M:%SZ')
        self._write(_status_payload(last_backup_at=old))
        status = get_backup_status(status_file=self.path, now=NOW)

        self.assertTrue(status['stale'])
        self.assertFalse(status['healthy'])
        self.assertTrue(status['should_warn'])
        self.assertIn('50 hours old', status['problem'])

    @override_settings(BACKUP_STALE_AFTER_HOURS=36)
    def test_backup_inside_threshold_is_not_stale(self):
        # 30h is over a day old but under the threshold: one missed nightly run
        # (or clock skew) must not raise an alarm, or the warning gets ignored.
        recent = (NOW - timedelta(hours=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
        self._write(_status_payload(last_backup_at=recent))
        status = get_backup_status(status_file=self.path, now=NOW)

        self.assertFalse(status['stale'])
        self.assertTrue(status['healthy'])

    def test_failed_attempt_is_reported_with_its_error(self):
        # The case that would otherwise look identical to "hasn't run yet".
        self._write(_status_payload(
            last_attempt_ok=False,
            error='pg_dump failed (exit 1): connection refused',
        ))
        status = get_backup_status(status_file=self.path, now=NOW)

        self.assertFalse(status['ok'])
        self.assertFalse(status['healthy'])
        self.assertTrue(status['should_warn'])
        self.assertIn('connection refused', status['problem'])

    def test_status_with_no_successful_backup_is_not_healthy(self):
        # Sidecar ran, reported success, but no dump file exists yet. That is
        # not a healthy state even though last_attempt_ok is true.
        self._write(_status_payload(last_backup_at=None, last_backup_file=None,
                                    backup_count=0))
        status = get_backup_status(status_file=self.path, now=NOW)

        self.assertFalse(status['healthy'])
        self.assertTrue(status['stale'])
        self.assertIn('No successful backup', status['problem'])

    def test_missing_file_does_not_raise(self):
        status = get_backup_status(status_file=os.path.join(self.tmp.name, 'nope.json'),
                                   now=NOW)
        self.assertFalse(status['available'])
        self.assertFalse(status['healthy'])
        self.assertIsNone(status['age_hours'])
        self.assertIn('No backup status file', status['problem'])

    def test_malformed_json_does_not_raise(self):
        # A status file caught mid-write, or truncated. This runs inside
        # each_context; raising here would break every admin page.
        self._write('{"last_attempt_ok": true, "last_backu')
        status = get_backup_status(status_file=self.path, now=NOW)

        self.assertFalse(status['available'])
        self.assertFalse(status['healthy'])
        self.assertTrue(status['should_warn'])
        self.assertIn('unreadable', status['problem'])

    def test_json_that_is_not_an_object_does_not_raise(self):
        self._write('["not", "a", "dict"]')
        status = get_backup_status(status_file=self.path, now=NOW)
        self.assertFalse(status['available'])
        self.assertIn('unreadable', status['problem'])

    def test_unparseable_timestamp_does_not_raise(self):
        self._write(_status_payload(last_backup_at='not-a-timestamp'))
        status = get_backup_status(status_file=self.path, now=NOW)

        self.assertTrue(status['available'])
        self.assertIsNone(status['age_hours'])
        self.assertFalse(status['healthy'])

    def test_missing_keys_do_not_raise(self):
        self._write({'last_attempt_ok': True})
        status = get_backup_status(status_file=self.path, now=NOW)

        self.assertTrue(status['available'])
        self.assertIsNone(status['last_backup_file'])
        self.assertFalse(status['healthy'])

    def test_every_documented_key_is_always_present(self):
        # Templates render these unconditionally, so the shape must not depend
        # on which failure path produced it.
        expected = {
            'available', 'healthy', 'ok', 'stale', 'age_hours', 'last_backup_at',
            'last_backup_file', 'last_backup_bytes', 'last_attempt_at',
            'oldest_backup_at', 'backup_count', 'retention_days', 'database',
            'error', 'problem', 'should_warn', 'size_display', 'status_file',
        }
        self._write(_status_payload())
        self.assertTrue(expected.issubset(get_backup_status(self.path, NOW).keys()))
        os.remove(self.path)
        self.assertTrue(expected.issubset(get_backup_status(self.path, NOW).keys()))


class BackupWarningSuppressionTests(SimpleTestCase):
    """
    A missing status file means different things in different environments.

    Keyed off DJANGO_ENV, not DEBUG: the test server runs DEBUG=True and still
    needs to be told its backups aren't running.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.missing = os.path.join(self.tmp.name, 'absent.json')

    @override_settings(DJANGO_ENV='PROD')
    def test_missing_file_warns_on_prod(self):
        self.assertTrue(get_backup_status(self.missing, NOW)['should_warn'])

    @override_settings(DJANGO_ENV='TEST')
    def test_missing_file_warns_on_test_server_despite_debug(self):
        self.assertTrue(get_backup_status(self.missing, NOW)['should_warn'])

    @override_settings(DJANGO_ENV=None)
    def test_missing_file_is_quiet_in_local_dev(self):
        # A developer not running the db-backup service shouldn't be nagged.
        self.assertFalse(get_backup_status(self.missing, NOW)['should_warn'])


class AdminBackupWarningTests(DatabaseTestCase):
    """
    The admin dashboard callout and Data Health panel that surface backup
    health (#1443), rendered through a real request rather than calling
    ``get_backup_status()`` in isolation.

    ``get_backup_status()`` being correct doesn't prove
    ``MakeabilityLabAdminSite.each_context`` actually wires ``BACKUP_STATUS``
    into the templates, or that the superuser gate in ``each_context`` is
    doing its job at the HTTP layer -- that's what these tests are for.
    """

    def setUp(self):
        super().setUp()
        User = get_user_model()
        self.superuser = User.objects.create_superuser(
            username="backupadmin", email="backupadmin@example.com", password="pw-for-test"
        )
        self.editor = User.objects.create_user(
            username="backupeditor",
            email="backupeditor@example.com",
            password="pw-for-test",
            is_staff=True,
        )
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.status_file = os.path.join(self.tmp.name, 'status.json')

    def _write_status(self, **overrides):
        """Write a status file for the *view* to read, timestamped relative to
        the real clock.

        This differs from the SimpleTestCase suites above on purpose. Those call
        ``get_backup_status(..., now=NOW)``, so ``_status_payload``'s fixed
        2026-08-07 timestamps stay correct forever. These tests go through the
        real admin views, which use the real clock — so a hard-coded timestamp
        reads as stale (``BACKUP_STALE_AFTER_HOURS = 36``) the day after it was
        written, turning a healthy fixture unhealthy and failing the suite for
        reasons that have nothing to do with the code under test. That is
        exactly what happened from 2026-08-08 onward (#1450).
        """
        now = datetime.now(timezone.utc)
        payload = {
            'last_attempt_at': _iso(now - timedelta(hours=3)),
            'last_backup_at': _iso(now - timedelta(hours=3)),
            'oldest_backup_at': _iso(now - timedelta(days=13)),
        }
        payload.update(overrides)
        with open(self.status_file, 'w', encoding='utf-8') as handle:
            json.dump(_status_payload(**payload), handle)
        return self.status_file

    def test_warning_shown_to_superuser_when_backup_unhealthy(self):
        self._write_status(last_attempt_ok=False,
                            error='pg_dump failed (exit 1): connection refused')
        with override_settings(BACKUP_STATUS_FILE=self.status_file):
            self.client.force_login(self.superuser)
            response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "database backups are not healthy")
        self.assertContains(response, "connection refused")

    def test_no_warning_when_backup_healthy(self):
        self._write_status()
        with override_settings(BACKUP_STATUS_FILE=self.status_file):
            self.client.force_login(self.superuser)
            response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "database backups are not healthy")

    def test_warning_hidden_from_non_superusers(self):
        """Only the maintainer can act on a backup failure, so don't alarm editors."""
        self._write_status(last_attempt_ok=False, error='connection refused')
        with override_settings(BACKUP_STATUS_FILE=self.status_file):
            self.client.force_login(self.editor)
            response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "database backups are not healthy")

    def test_data_health_panel_always_shown_even_when_healthy(self):
        """
        Unlike the ``/admin/`` callout, the Data Health panel is rendered
        unconditionally -- "when did it last succeed?" is worth showing even
        when nothing is wrong.
        """
        self._write_status()
        with override_settings(BACKUP_STATUS_FILE=self.status_file):
            self.client.force_login(self.superuser)
            response = self.client.get(reverse("admin:data_health_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Database backups")
        self.assertContains(response, "Healthy")
        self.assertContains(response, "makeability-2026-08-07.sql.gz")


class FormatBytesTests(SimpleTestCase):
    def test_formats_common_sizes(self):
        self.assertEqual(format_bytes(512), '512 B')
        self.assertEqual(format_bytes(12684), '12.4 KB')
        self.assertEqual(format_bytes(5 * 1024 * 1024), '5.0 MB')

    def test_handles_missing_and_garbage(self):
        self.assertEqual(format_bytes(None), '—')
        self.assertEqual(format_bytes('nonsense'), '—')
