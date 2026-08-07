"""
Read the database-backup status file written by the ``db-backup`` sidecar (#1443).

The sidecar (``scripts/pg_backup.sh``, wired up in ``docker-compose.yml``) writes
a small JSON file after every pass — successful or not — to a volume this
container mounts read-only. This module turns that file into a dict the admin
dashboard, the Data Health page, and ``/version.json`` all render.

Why this exists at all: the dumps land in a Docker named volume on a host with
no shell access, inside a ``PGDATA`` this container cannot even traverse. The
status file is the only channel through which backup health is observable. That
makes *this* module's failure modes important — it must degrade to "unknown"
rather than raise, or a missing backup would take the admin down with it.

Usage::

    from website.utils.backup_status import get_backup_status
    status = get_backup_status()
    if not status['healthy']:
        print(status['problem'])   # e.g. "Last backup is 51 hours old"
"""

import json
import logging
import os
from datetime import datetime, timezone

from django.conf import settings

logger = logging.getLogger(__name__)

#: Shape returned when the status file can't be read or understood at all.
#: Deliberately not an exception: a broken status file must not break /admin.
_UNKNOWN = {
    'available': False,
    'healthy': False,
    'ok': None,
    'stale': False,
    'age_hours': None,
    'last_backup_at': None,
    'last_backup_file': None,
    'last_backup_bytes': None,
    'last_attempt_at': None,
    'oldest_backup_at': None,
    'backup_count': None,
    'retention_days': None,
    'database': None,
    'error': None,
    # Kept in the unknown shape too so templates can render every key
    # unconditionally instead of guarding each one.
    'problem': None,
    'should_warn': False,
    'size_display': '—',
    'status_file': None,
}


def _parse_iso(value):
    """Parse an ISO-8601 UTC timestamp from the status file, or return None.

    The sidecar writes ``...Z``; ``fromisoformat`` only learned to accept the
    ``Z`` suffix in Python 3.11, so normalize it rather than relying on that.
    """
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return None


def format_bytes(num):
    """Render a byte count as a short human string ('12.4 MB'), or '—'."""
    if num is None:
        return '—'
    try:
        num = float(num)
    except (TypeError, ValueError):
        return '—'
    for unit in ('B', 'KB', 'MB', 'GB'):
        if abs(num) < 1024.0 or unit == 'GB':
            return f"{num:.0f} {unit}" if unit == 'B' else f"{num:.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} GB"


def get_backup_status(status_file=None, now=None):
    """
    Return a dict describing database-backup health. Never raises.

    Args:
        status_file: path to status.json. Defaults to ``settings.BACKUP_STATUS_FILE``.
        now: aware ``datetime`` used as "now" (for tests). Defaults to real UTC now.

    Returns:
        dict with at least ``available`` (was the file readable), ``healthy``
        (readable AND last attempt succeeded AND not stale), ``problem`` (a
        one-line human explanation when not healthy, else None), plus the
        parsed fields and a few display-formatted extras.

    A note on the three unhealthy states, which mean different things:
      * ``available=False`` — no status file. Either backups have never run on
        this host, or the volume isn't mounted. Expected in local dev.
      * ``ok=False`` — the sidecar ran and *failed*; ``error`` says why.
      * ``stale=True`` — the last pass may have succeeded, but the newest dump
        is older than ``BACKUP_STALE_AFTER_HOURS``, so backups have stopped.
    """
    if status_file is None:
        status_file = getattr(settings, 'BACKUP_STATUS_FILE', None)
    if now is None:
        now = datetime.now(timezone.utc)

    status = dict(_UNKNOWN)
    status['status_file'] = status_file

    if not status_file or not os.path.exists(status_file):
        status['problem'] = 'No backup status file found.'
        # On a server this is a real problem — the sidecar never ran, or the
        # status volume isn't mounted. In local dev, where a developer may
        # simply not be running the db-backup service, it is expected and must
        # not nag. Keyed off DJANGO_ENV rather than DEBUG on purpose: the test
        # server runs DEBUG=True and still needs to be warned.
        status['should_warn'] = getattr(settings, 'DJANGO_ENV', None) in ('PROD', 'TEST')
        return status

    try:
        with open(status_file, 'r', encoding='utf-8') as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError('status file is not a JSON object')
    except (OSError, ValueError) as exc:
        # Truncated file, bad JSON, permissions — all reported the same way.
        # A file that exists but can't be parsed is always worth warning about.
        logger.warning("Could not read backup status file %s: %s", status_file, exc)
        status['problem'] = f'Backup status file is unreadable ({exc}).'
        status['should_warn'] = True
        return status

    status['available'] = True
    status['ok'] = bool(data.get('last_attempt_ok'))
    status['error'] = data.get('error') or None
    status['database'] = data.get('database')
    status['last_backup_file'] = data.get('last_backup_file')
    status['last_backup_bytes'] = data.get('last_backup_bytes')
    status['backup_count'] = data.get('backup_count')
    status['retention_days'] = data.get('retention_days')
    status['last_backup_at'] = _parse_iso(data.get('last_backup_at'))
    status['last_attempt_at'] = _parse_iso(data.get('last_attempt_at'))
    status['oldest_backup_at'] = _parse_iso(data.get('oldest_backup_at'))
    status['size_display'] = format_bytes(status['last_backup_bytes'])

    stale_after = getattr(settings, 'BACKUP_STALE_AFTER_HOURS', 36)
    if status['last_backup_at'] is not None:
        age = (now - status['last_backup_at']).total_seconds() / 3600.0
        status['age_hours'] = round(age, 1)
        status['stale'] = age > stale_after
    else:
        # A readable status file that names no dump means nothing has ever been
        # backed up successfully here — treat that as stale, not as healthy.
        status['stale'] = True

    status['healthy'] = bool(status['ok']) and not status['stale']

    # A status file exists, so whatever it says is worth showing everywhere,
    # local dev included: a failing sidecar is a bug wherever it happens.
    status['should_warn'] = not status['healthy']

    if status['healthy']:
        status['problem'] = None
    elif not status['ok']:
        status['problem'] = f"Last backup attempt failed: {status['error'] or 'unknown error'}"
    elif status['age_hours'] is None:
        status['problem'] = 'No successful backup has been recorded yet.'
    else:
        status['problem'] = (
            f"Last backup is {status['age_hours']:.0f} hours old "
            f"(expected at most {stale_after})."
        )
    return status
