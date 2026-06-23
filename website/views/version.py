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
      "server": "gunicorn/23.0.0"
    }

The ``server`` field is the WSGI server's self-reported ``SERVER_SOFTWARE``
(``gunicorn/<ver>`` vs. Django's ``WSGIServer/<ver> CPython/<ver>``), read off
the live request -- it's the ground-truth answer to *"is this actually running
Gunicorn?"* after the #1034 swap, not an inference from env vars or git_sha.
"""

import json
import logging
import os

from django.conf import settings
from django.http import JsonResponse

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
    payload = {
        "version": settings.ML_WEBSITE_VERSION,
        "description": settings.ML_WEBSITE_VERSION_DESCRIPTION,
        "environment": settings.DJANGO_ENV or "unknown",
        "git_sha": build_info["git_sha"],
        "built_at": build_info["built_at"],
        # WSGI server handling this request: "gunicorn/<ver>" under #1034,
        # "WSGIServer/<ver> CPython/<ver>" if the dev runserver is somehow live.
        "server": request.META.get("SERVER_SOFTWARE", "unknown"),
    }
    response = JsonResponse(payload)
    response["Cache-Control"] = "no-store"
    return response
