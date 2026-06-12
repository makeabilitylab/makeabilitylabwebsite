# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Django website for the Makeability Lab at UW CSE (HCI / accessibility / urban computing research). Single Django app (`website`) inside a project named `makeabilitylab`, served via PostgreSQL and Docker. Python 3.13, Django 5.2 LTS, PostgreSQL 16.

## Running the site (local dev)

Everything runs in Docker. There is no native venv path — work inside the container.

```bash
# First time: build image, then start
docker build . -t makelab_image
docker-compose -f docker-compose-local-dev.yml up

# Convenience wrapper (supports --build, --buildnc, --verbose)
./run-docker-local-dev.sh

# Stop
docker-compose down
```

Site → http://localhost:8571 (container's 8000 mapped to host's 8571). Postgres exposed at host port `6543` (container 5432). The project root is bind-mounted to `/code`, so edits hot-reload — no rebuild needed unless `Dockerfile` or `requirements.txt` changes.

To get a shell inside the running container:

```bash
docker exec -it makeabilitylabwebsite-website-1 bash
# Some Docker Compose versions: makeabilitylabwebsite_website_1
```

Inside the container, run Django commands as usual: `python manage.py <cmd>`.

A superuser is required to use `/admin` and add content; create one with `python manage.py createsuperuser` inside the container.

## Tests and accessibility checks

- Tests: `python manage.py test` (inside container). Note: `website/tests.py` is currently empty — there is no meaningful test suite to run.
- Accessibility (Pa11y CI + Axe, WCAG 2.0 AA): start the site, then `docker-compose -f docker-compose-local-dev.yml --profile testing run --rm a11y`. URLs to scan are configured in `.pa11yci.json`. Run this before submitting UI changes.

## Deployment

- **Push to `master`** → auto-deploys to `makeabilitylab-test.cs.washington.edu` via webhook.
- **Push a SemVer tag (e.g. `git tag 2.3.2 && git push --tags`)** → deploys to production `makeabilitylab.cs.washington.edu`.
- Bump `ML_WEBSITE_VERSION` and `ML_WEBSITE_VERSION_DESCRIPTION` in `makeabilitylab/settings.py` when cutting a release.
- Build logs: `<host>/logs/buildlog.txt`. Application logs: `<host>/logs/debug.log`. See `docs/DEPLOYMENT.md` for SSH paths on `recycle.cs.washington.edu`.

## Architecture

### Project layout

- `manage.py` → Django entry point, uses `makeabilitylab.settings`.
- `makeabilitylab/` → Django project (settings, root URLconf, WSGI). Root URLconf mounts `website.urls` at `/`, `admin.site.urls` at `/admin/`, ckeditor at `/ckeditor/`, and django-debug-toolbar at `/__debug__/`.
- `website/` → the single Django app. All models, views, admin, URLs, templates live here.
- `makeabilitylabwebsite/` → **not** a Python package; legacy folder holding deploy shell scripts (`rebuildanddeploy.sh`, `command`, `command-test`) used by the production deploy webhook. Don't confuse it with the Django project package above.
- `sortedm2m_filter_horizontal_widget/` → a vendored, locally-modified fork of the upstream `sortedm2m-filter-horizontal-widget` package (upstream is incompatible with Django 5.2). It is listed in `INSTALLED_APPS`; treat it as project source code, not a third-party library.
- `media/` → user-uploaded content (publications PDFs, images, talks). Bind-mounted, persists across container restarts.
- `static/` → output of `collectstatic`; do not edit by hand. Source assets live under `website/static/`.

### The `website` app is split by concern, one file per model

Each domain concept gets a dedicated file across three parallel directories. When adding a new entity, create files in all three:

- `website/models/<thing>.py` — the model. All models are re-exported from `website/models/__init__.py`, so import as `from website.models import Person, Publication, …`.
- `website/admin/<thing>_admin.py` — the ModelAdmin, registered via `@admin.register(...)` decorator. Imported in `website/admin/__init__.py` purely to trigger registration.
- `website/views/<thing>.py` — view functions, re-exported via `website/views/__init__.py` (mostly `from .x import *`).

Custom admin organization lives in `website/admin/admin_site.py` (`MakeabilityLabAdminSite`). It overrides Django's default app-based grouping with workflow-based groups: Artifacts (Publications/Talks/Posters/Videos), People & News, Projects & Media, Grants & Funding, Configuration, Administration. Section order and which models go in which group are defined in `CUSTOM_GROUPS`. Update this when adding a new top-level model that should appear on the admin index.

### Key model relationships

- A `Publication` is the central artifact. `Talk`, `Poster`, `Video` are related artifacts; the admin tip is to start from the Publication's edit page so shared fields (title, authors, date, venue) auto-fill on the children.
- `Person` ↔ `Project` via `ProjectRole` (with start/end dates). The `auto_close_project_roles` management command (run on every container start) closes expired roles.
- `Award` (separate from `Publication.award`) represents external recognitions; sectioned on the public Awards page by `AwardType`. Paper-level awards are NOT `Award` — they're on `Publication.award`. Keep this distinction in mind when modifying either.
- Many M2M relations use `SortedManyToManyField` (vendored `sortedm2m` widget) so display order is editor-controlled, not alphabetical.

### URL routing quirks

- `website/urls.py` exposes both `/projects/<name>/` and `/project/<name>/` (singular) for the same view — both must keep working; project URLs are linked from external sources.
- `/media/publications/<filename>` is served by the custom `serve_pdf` view (not Django's static serve), which does **fuzzy filename matching** so stale external links to renamed PDFs still resolve. Don't replace it with a plain static route.
- In `DEBUG=True`, `/media/...` is also served by Django's `serve()`. In production, the web server handles `/media/` directly.

### Settings, config, and environment

- `makeabilitylab/settings.py` reads `config.ini` at project root for production secrets and DB credentials. `config.ini` is **not** committed — production mounts it as a Docker volume.
- `DEBUG` resolution order: `DJANGO_ENV=PROD` forces False → `config.ini [Django] DEBUG` → `DJANGO_ENV=DEBUG` forces True → default False.
- Without a `[Postgres]` section in `config.ini`, Django falls back to the dockerized dev DB (`db:5432`, user `admin`, pw `password`, db `makeability`) defined in `docker-compose-local-dev.yml`.
- `TIME_ZONE = 'America/Los_Angeles'`. `ML_WEBSITE_VERSION` in settings is shown in the admin header and used in release tagging.

### Container startup side effects (`docker-entrypoint.sh`)

Every container start runs, in order: `collectstatic` → `makemigrations` → `migrate` → `makemigrations website` → `migrate website` → `delete_unused_files` → `thumbnail_cleanup` → `generate_slugs_for_old_news_items` → `auto_close_project_roles` → `remove_year_from_forum_name` → `fix_sortedm2m_columns` → `runserver 0.0.0.0:8000`. The repeated `makemigrations website` step is intentional (fixes first-run issues). If you add a one-shot data migration command under `website/management/commands/`, decide whether it belongs in this startup sequence.

### Image handling

`image_cropping` + `easy_thumbnails` work together: cropping defines the crop box, easy_thumbnails generates sized variants. `THUMBNAIL_PROCESSORS` is configured so crop_corners runs before the default chain. Image processing requires ImageMagick (installed in the Dockerfile) and a custom `imagemagick-policy.xml` is mounted into `/etc/ImageMagick-6/policy.xml` to enable PDF processing (see issue #974).

### Rich text

News items use `django-ckeditor`. Uploaded files via CKEditor land under `media/uploads/`, with filenames generated by `website.utils.fileutils.get_ckeditor_image_filename`.

## VSCode / Dev Container

`.devcontainer/devcontainer.json` opens VSCode inside the `website` service, installing Python, Pylance, the Django syntax extension, and djlint inside the container. The Dev Container connects as `root` (not `apache`) to avoid file-permission edits failing on WSL2. djlint is the formatter for `*.html` files under `templates/`; `**/templates/**/*.html` is associated with the `django-html` language.

## Coding conventions for this repo

- Favor simple, standard approaches over new frameworks/libraries. The
  frontend is Bootstrap + jQuery + vanilla JS; match that. Do not introduce
  React or a frontend build step unless explicitly requested.
- Accessibility is a first-class requirement: write a11y-correct markup by
  default and keep changes WCAG 2.0 AA compliant (the Pa11y service enforces
  this on UI changes).
- Document to language convention: JSDoc for JS, docstrings for Python views/
  models/management commands. Add usage examples for non-obvious logic.
- HTML/Django templates: 2-space indentation; djlint is the formatter.
- Prefer clarity over cleverness; mark placeholders and TODOs clearly.

## Pull request conventions (from CONTRIBUTING.md)

- One issue per branch; branch name starts with the issue number, e.g. `335-adding-hover-to-landing-page`.
- UI changes require before/after screenshots or mockups in the PR (see issue #287 as a reference).
- Run the Pa11y a11y service before submitting any UI change.
- PRs target `master`.
