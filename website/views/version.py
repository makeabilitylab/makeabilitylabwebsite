"""
Machine-readable version / build-info endpoint (#1366).

Exposes the running code version as JSON at ``/version/`` (and ``/version.json``)
so the deployed build can be checked without fetching a full page and scraping
the ``<!-- Makeability Lab website version ... -->`` comment in ``base.html``.

``version`` / ``description`` / ``environment`` come straight from
``settings.py``. ``git_sha`` and ``built_at`` are captured *once at container
start* by ``docker-entrypoint.sh`` (which writes them into the build-info file at
:data:`BUILD_INFO_PATH`) rather than per request -- that avoids running ``git``
on every hit or needing git in the runtime image. Both fall back to
``"unknown"`` when the file is missing (e.g. local dev without the entrypoint).

These two fields are what actually answer *"is prod stale?"*: a bumped tag that
never deployed shows an old ``git_sha`` / ``built_at`` at a glance. No new info
is disclosed -- ``version`` / ``description`` are already public via the HTML
comment.

Example::

    GET /version/
    {
      "version": "2.16.3",
      "description": "Fix the project listing page ...",
      "environment": "PROD",
      "git_sha": "02909b0",
      "built_at": "2026-06-21T18:30:00-07:00",
      "server": "gunicorn/23.0.0",
      "log_to_file": true,
      "log_file": "/code/media/debug.log",
      "log_rotation": "ConcurrentRotatingFileHandler"
    }

The ``server`` field is the WSGI server's self-reported ``SERVER_SOFTWARE``
(``gunicorn/<ver>`` vs. Django's ``WSGIServer/<ver> CPython/<ver>``), read off
the live request -- it's the ground-truth answer to *"is this actually running
Gunicorn?"* after the #1034 swap, not an inference from env vars or git_sha.

``log_to_file`` / ``log_file`` report whether the ``LOGGING`` file handler is live
or degraded to a NullHandler, and which path it resolved to (#1283). We have no
console access on the -test or prod servers, so without this a bad log directory
would silently blackhole every log record with no way to notice: ``log_to_file:
false`` means the app is running blind, and ``log_file`` says which directory was
at fault. Nothing new is disclosed -- the path is derivable from the public repo.

``log_rotation`` names the live rotation handler class (#1439). Gunicorn runs 3
workers over one debug.log, so it must be ``ConcurrentRotatingFileHandler``;
anything else means the multiprocess-safe handler degraded (package missing from
the image, or no usable lock directory) and workers can clobber each other's
rotated files again.

Note that ``log_to_file: true`` only means the log *directory* was writable at
startup. To confirm records are really landing, tail the file over SSH at
``/cse/web/research/makelab/www[-test]/debug.log`` -- there is no web path to the
log (the old ``/logs/`` URL is gone; see docs/DEPLOYMENT.md).
"""

import json
import logging
import os

from django.conf import settings
from django.http import JsonResponse

from website.utils.backup_status import get_backup_status

# Module logger (configured in settings.LOGGING).
_logger = logging.getLogger(__name__)

# Small JSON file written by docker-entrypoint.sh at container start. Not
# committed (gitignored); the view tolerates its absence.
BUILD_INFO_PATH = os.path.join(settings.BASE_DIR, "build-info.json")


def _read_build_info():
    """
    Return ``{"git_sha": ..., "built_at": ...}`` read from the build-info file,
    falling back to ``"unknown"`` for any missing/unreadable value. Never raises
    -- a broken or absent file just yields the fallbacks.
    """
    fallback = {"git_sha": "unknown", "built_at": "unknown"}
    try:
        with open(BUILD_INFO_PATH) as f:
            data = json.load(f)
    except FileNotFoundError:
        return fallback
    except (OSError, ValueError) as e:
        _logger.warning("Could not read build-info file %s: %s", BUILD_INFO_PATH, e)
        return fallback
    return {
        "git_sha": data.get("git_sha") or "unknown",
        "built_at": data.get("built_at") or "unknown",
    }


def version(request, format=None):
    """
    GET /version/ (and /version.json) -> JSON build/version info.

    Unauthenticated and free of sensitive data. Sets ``Cache-Control: no-store``
    so Apache or any intermediary can't serve a stale version string -- the whole
    point is to read the *current* deployed build.

    ``format`` is accepted (and ignored) so the DRF ``format_suffix_patterns``
    wrapper applied in ``website/urls.py`` doesn't choke on the suffixed route.
    """
    build_info = _read_build_info()
    backup = get_backup_status()
    payload = {
        "version": settings.ML_WEBSITE_VERSION,
        "description": settings.ML_WEBSITE_VERSION_DESCRIPTION,
        "environment": settings.DJANGO_ENV or "unknown",
        "git_sha": build_info["git_sha"],
        "built_at": build_info["built_at"],
        # WSGI server handling this request: "gunicorn/<ver>" under #1034,
        # "WSGIServer/<ver> CPython/<ver>" if the dev runserver is somehow live.
        "server": request.META.get("SERVER_SOFTWARE", "unknown"),
        # Is the LOGGING file handler live, and where does it point (#1283)? False
        # means it degraded to a NullHandler and this server is logging nowhere --
        # the only remote way to notice, since we have no console on -test/prod.
        "log_to_file": settings.LOG_TO_FILE,
        "log_file": settings.LOG_FILE,
        # Which rotation handler is live (#1439). Anything other than
        # "ConcurrentRotatingFileHandler" means the multiprocess-safe handler
        # degraded and Gunicorn's workers can race on rollover again.
        "log_rotation": settings.LOG_ROTATION,
        # Database backup health (#1443). The nightly dump lands in a Docker
        # volume on a host with no shell, so this is the only way to check it
        # without logging into /admin. backup_ok false means either the last
        # pass failed or the newest dump has gone stale -- backup_problem says
        # which. No paths or error internals beyond that: this endpoint is
        # public.
        "backup_ok": backup["healthy"],
        "last_backup_at": (
            backup["last_backup_at"].isoformat() if backup["last_backup_at"] else None
        ),
        "backup_age_hours": backup["age_hours"],
        "backup_count": backup["backup_count"],
    }
    response = JsonResponse(payload)
    response["Cache-Control"] = "no-store"
    return response
