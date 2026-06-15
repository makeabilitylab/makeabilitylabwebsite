"""
Test-only Django settings.

Run with:
    python manage.py test website --settings=makeabilitylab.settings_test

Why this exists
---------------
``website/migrations/`` is gitignored, so every environment (laptop, CI, the
servers) carries its own migration history. That drift intermittently breaks a
fresh test-DB build with ``column "..." already exists`` (see #1267 and
CLAUDE.md). Setting ``MIGRATION_MODULES = {'website': None}`` tells Django to
ignore the website app's migration history entirely and build its tables
directly from the current models during test-DB setup (run_syncdb), which is
both reproducible across environments and the durable fix for that flakiness.

Only the *website* app is affected; third-party apps (admin, auth, ckeditor,
sortedm2m, easy_thumbnails, image_cropping, ...) keep their shipped migrations.
"""
import os

from makeabilitylab.settings import *  # noqa: F401,F403

# Build website tables from models instead of replaying gitignored migrations.
MIGRATION_MODULES = {"website": None}

# Let CI point the database at its Postgres service container. Locally (inside
# the website container) these env vars are unset, so we inherit HOST='db' from
# the base settings fallback; CI sets DATABASE_HOST=localhost.
DATABASES["default"]["HOST"] = os.environ.get(  # noqa: F405
    "DATABASE_HOST", DATABASES["default"]["HOST"]  # noqa: F405
)
DATABASES["default"]["PORT"] = os.environ.get(  # noqa: F405
    "DATABASE_PORT", DATABASES["default"].get("PORT", "5432")  # noqa: F405
)

# The base settings wire a RotatingFileHandler to /code/media/debug.log (a
# container path). Django evaluates LOGGING at startup, so on any host without
# that directory — a CI runner, a fresh checkout — django.setup() crashes
# before a single test runs. Swap just the 'file' handler for a no-op; this
# keeps every logger's handler reference valid while never touching disk.
LOGGING["handlers"]["file"] = {"class": "logging.NullHandler"}  # noqa: F405

# Speed up the auth tests (Data Health suite creates real superuser rows).
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
