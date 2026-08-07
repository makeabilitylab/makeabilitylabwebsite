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

- Tests: `python manage.py test website --settings=makeabilitylab.settings_test` (inside container). The tests live in the `website/tests/` package (one `test_*.py` per concern; Django auto-discovers them) with shared DB fixtures in `website/tests/base.py`. The suite has two styles:
  - **Unit** — `SimpleTestCase` + `MagicMock` for pure logic (formatters, BibTeX generation, etc.); no DB, runs in ms.
  - **Integration** — `DatabaseTestCase` (subclass of Django's `TestCase`, in `tests/base.py`) for view / queryset / template regressions; each test runs in a transaction and rolls back. Has fixture helpers `make_person` / `make_publication` / `make_talk` / `make_news_item`.
  - When fixing a bug reachable through a real queryset, URL, or view, add a regression test in the matching style before applying the fix (matches the tests-first workflow).
  - **Always use the `--settings=makeabilitylab.settings_test` shim.** It sets `MIGRATION_MODULES = {'website': None}` so the test DB is built directly from the current models, sidestepping the gitignored, per-environment `website/migrations/` history. This is the durable fix for #1267 — without it, a fresh test DB can fail at creation with `column "..." already exists` (old workaround: `docker exec makeabilitylabwebsite-db-1 psql -U admin -d postgres -c "DROP DATABASE IF EXISTS test_makeability;"`).
  - **CI:** `.github/workflows/test.yml` runs this same command on every push to `master` and every PR (free/unlimited for this public repo). It reports a green ✓ / red ✗ — it does not block pushes or the deploy. See the testing roadmap in #1278.
  - **Coverage (#1278 item 4):** the CI `test` job wraps the suite in `coverage run` and publishes a table to the run's Summary; config is in `.coveragerc` (measures the `website` app, branch coverage on). It's **report-only** — no `--fail-under` gate; the number targets backfill. Run locally inside the container: `pip install -r requirements-dev.txt`, then `coverage run manage.py test website --settings=makeabilitylab.settings_test && coverage report` (or `coverage html` for a browsable `htmlcov/`).
- Accessibility (Pa11y CI + Axe, WCAG 2.0 AA): start the site, then `docker-compose -f docker-compose-local-dev.yml --profile testing run --rm a11y`. URLs to scan are configured in `.pa11yci.json`. Run this before submitting UI changes.

## Deployment

- **Push to `master`** → auto-deploys to `makeabilitylab-test.cs.washington.edu` via webhook.
- **Push a SemVer tag (e.g. `git tag 2.3.2 && git push --tags`)** → deploys to production `makeabilitylab.cs.washington.edu`.
- Bump `ML_WEBSITE_VERSION` and `ML_WEBSITE_VERSION_DESCRIPTION` in `makeabilitylab/settings.py` when cutting a release.
- Application logs: read `debug.log` over SSH on `makelab1`/`makelab2`/`recycle` under `/cse/web/research/makelab/www[-test]/`. Build logs only reach you via the deploy email. **The web `/logs/` URL is gone — every path under it 404s on both hosts.** Confirm what a server is running with `/version.json` (`git_sha`, not `built_at`). See `docs/DEPLOYMENT.md`.

### Server access model (important — shapes how anything ships to prod/test)

The maintainer does **not** have shell or admin access to the test or production servers. UW CSE IT (Jason Howe) owns and configured both; Apache/web-server and file-permission changes go through them, and much of the deployed tree is `apache:makelab`-owned. The only available controls and visibility are:

- **Deploys are push-only.** Push to `master` → test; push a SemVer tag → prod. There is **no way to run `docker` or `manage.py` directly** on either server.
- **SSH is read-mostly and limited to one jump host.** The maintainer can SSH to `recycle.cs.washington.edu` and read files on the shared CSE filesystem under `/cse/web/research/makelab/` (logs, the `media/` dir, `secret/config.ini`). There is **no SSH access to the host that runs the Docker stack** and no passwordless sudo.
- **The database is not reachable directly.** Prod Postgres runs as the `db` Docker container, bound to the Docker host's **loopback only**, so there is no tunnel/network path to it from a laptop or from `recycle`. (Credentials are moot anyway — see below.)
- **Therefore, any operation against prod/test data must run *inside* the container.** Ship it as a management command wired into `docker-entrypoint.sh` (the established one-shot pattern) and verify via the logs. For one-off offline analysis, request a DB snapshot from CSE IT rather than trying to connect remotely.
- **Never write personal or sensitive data to web-served paths** (`media/`, `static/`, `logs/`) — everything under them is publicly downloadable. (A stale public `dumped_data.json` was exactly this mistake.)

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

**Admin users & permissions (#1125):** editing access is structured as personal accounts assigned to one of two declarative groups — `Editors` (PhD/staff, full content) and `Contributors` (ugrads/interns, submit-and-review, no deletes) — plus superuser (maintainer + a break-glass backup). Grant, Award, and all account-administration models are superuser-only. The groups' permission sets are the source of truth in `setup_admin_groups` (run on every container start via `docker-entrypoint.sh`, pinned by `test_setup_admin_groups`); group *membership* is managed in `/admin`. When adding a new model that editors should manage, add it to `EDITORS_MODELS`/`CONTRIBUTORS_SPEC` and update the test. Full reference + onboarding/offboarding runbook: `docs/ADMIN_USERS_AND_GROUPS.md`.

### Key model relationships

- A `Publication` is the central artifact. `Talk`, `Poster`, `Video` are related artifacts; the admin tip is to start from the Publication's edit page so shared fields (title, authors, date, venue) auto-fill on the children.
- `Person` ↔ `Project` via `ProjectRole` (with start/end dates). The `auto_close_project_roles` management command (run on every container start) closes expired roles.
- `Award` (separate from `Publication.award`) represents external recognitions; sectioned on the public Awards page by `AwardType`. Paper-level awards are NOT `Award` — they're on `Publication.award`. Keep this distinction in mind when modifying either.
- Many M2M relations use `SortedManyToManyField` (vendored `sortedm2m` widget) so display order is editor-controlled, not alphabetical.

### URL routing quirks

- `website/urls.py` exposes both `/projects/<name>/` and `/project/<name>/` (singular) for the same view — both must keep working; project URLs are linked from external sources.
- `/media/publications/<filename>` is served by the custom `serve_pdf` view (not Django's static serve), which does **fuzzy filename matching** so stale external links to renamed PDFs still resolve. Don't replace it with a plain static route.
- In `DEBUG=True`, `/media/...` is also served by Django's `serve()`. In production, the web server handles `/media/` directly.

### Public REST API (`website/api/`, #1268)

A public, **read-only** DRF API at `/api/v1/` over already-public content
(publications, projects, grants, people, project leadership). Built on the
already-bundled `djangorestframework` (previously an unused dependency). Code
lives in the `website/api/` package (`serializers.py`, `views.py`, `urls.py`,
`middleware.py`), mounted by the **root** URLconf (`makeabilitylab/urls.py`),
configured by the `REST_FRAMEWORK` block in `settings.py`. GET-only, no auth, no
throttle (data is already public); paginated (`?page_size=`, max 100); every
payload uses absolute URLs. Cross-origin requests are allowed on `/api/` only
via the in-repo `ApiCorsMiddleware` (no `django-cors-headers` dependency).
`Person.email` is intentionally not serialized. Projects are gated to
`is_visible=True`; the people list is scoped to actual members (those with a
Position). Image fields follow one rule (#1432): `thumbnail` is a cropped, sized
derivative built by `website.utils.thumbnail_utils.get_cropped_thumbnail` (sizes
in `serializers.py`; keep each size's aspect ratio equal to the model's
`ImageRatioField`), `image_original` is the raw upload; `warm_api_thumbnails`
pre-generates the derivatives at container start. When adding a resource, follow
the existing viewset/serializer pattern and keep `v1` fields additive-only
(breaking changes → `v2`). Full reference: `docs/API.md`. Tests:
`website/tests/test_api.py`.

### Settings, config, and environment

- **Compose files per environment:** the servers run `docker-compose.yml` (test *and* prod — `makeabilitylabwebsite/rebuildanddeploy.sh` runs `docker compose up` with no `-f`, so it always picks the default `docker-compose.yml`; it only varies per-host env vars). Local dev runs `docker-compose-local-dev.yml` (passed explicitly with `-f`). `docker-compose-local-dev.yml` is **never** used on the servers.
- **Per-host wiring** (set by `rebuildanddeploy.sh`): test host `docker-test2` → `DJANGO_ENV=TEST`, mounts `secret/config-test.ini` + `www-test/` media; prod host `grabthar` → `DJANGO_ENV=PROD`, mounts `secret/config.ini` + `www/` media.
- `makeabilitylab/settings.py` reads `config.ini` (mounted at the project root, **not** committed) for `SECRET_KEY`, `DEBUG`, and `ALLOWED_HOSTS`.
- **Prod/test `config.ini` has only a `[Django]` section — no `[Postgres]` section.** Per `settings.py`, a missing `[Postgres]` section means Django uses the fallback `DATABASES` default (`HOST='db'`) — i.e. the dockerized `db` service of the active compose file. A `[Postgres]` section, if added, would override it. So the DB is the in-stack `db` container in **every** environment (no external Postgres); on the servers that's the `db` service in `docker-compose.yml`.
- `DEBUG` resolution order: `DJANGO_ENV=PROD` forces False → `config.ini [Django] DEBUG` → `DJANGO_ENV=DEBUG` forces True → default False.
- `TIME_ZONE = 'America/Los_Angeles'`. `ML_WEBSITE_VERSION` in settings is shown in the admin header and used in release tagging.
- **Logging (#1283):** `debug.log` lives at `LOG_DIR/debug.log`, where `LOG_DIR` is `$ML_LOG_DIR` or `<BASE_DIR>/media` (`/code/media` in the container). Keep it inside `MEDIA_ROOT` — that's the tree bind-mounted to the shared CSE filesystem, so it's what makes the log readable over SSH at all. `ML_LOG_DIR` is unset everywhere today; it exists for non-`/code` hosts. `MEDIA_ROOT` is web-served, so never log anything sensitive. If the dir isn't writable the file handler degrades to a `NullHandler` rather than crashing `django.setup()`, and since there's no console on the servers that state surfaces via `/version.json` (`log_to_file`) and a superuser-only callout on the admin dashboard. Rotation uses `concurrent-log-handler` (#1439) because Gunicorn's 3 workers share one file — the stdlib `RotatingFileHandler` races on rollover across processes. Its lock file goes in a per-uid temp dir (`/tmp/makelab-log-locks-<uid>`), never the web-served media root and never shared across users. If the package isn't importable (the bind-mounted checkout can be ahead of the image's site-packages) or no lock dir is usable, the handler degrades to the stdlib `RotatingFileHandler` instead of crashing `django.setup()`; `/version.json` reports which one is live as `log_rotation`. `django.db.backends` is pinned to INFO so per-query SQL doesn't dominate the log (or the lock).

- **Database backups (#1443):** a `db-backup` sidecar service (in *both* compose files) runs `scripts/pg_backup.sh` hourly; the script is a single pass that writes one dated `pg_dump | gzip` per UTC day to `pg_backups/` **inside the postgres data volume**, prunes past `BACKUP_RETENTION_DAYS` (14, never the newest dump), and writes `status.json` to a small volume the website container mounts read-only. Dumps go inside the data volume on purpose — that's the volume CSE IT snapshots, so every snapshot carries a consistent restore point. Two things are load-bearing: the sidecar's `entrypoint` **must** stay overridden (the postgres image's own entrypoint would start a second server on that `PGDATA`), and the scheduling loop lives in the compose file rather than in the script (`docker compose up -d` only recreates containers whose *config* changed, so a loop inside the bind-mounted script would run stale code forever after a deploy). Django only ever *reads* the status: `website/utils/backup_status.py` → `/version.json` (`backup_ok`), a superuser callout on the admin dashboard shown only when stale/failed, and a panel on Data Health. Dumps contain `Person.email` — never move one under a web-served path. Restore procedure, the `initdb`-refuses-a-non-empty-directory gotcha, and the two Docker-based restore harnesses (`scripts/test_backup_restore*.sh`): `docs/BACKUPS.md`.

### Container startup side effects (`docker-entrypoint.sh`)

Every container start runs, in order: `collectstatic` → `makemigrations` → `migrate` → `makemigrations website` → `migrate website` → `delete_unused_files` → `thumbnail_cleanup` → `generate_slugs_for_old_news_items` → `auto_close_project_roles` → `remove_year_from_forum_name` → `fix_sortedm2m_columns` → `seed_sidewalk_participants` → `warm_api_thumbnails` → `runserver 0.0.0.0:8000`. The repeated `makemigrations website` step is intentional (fixes first-run issues). If you add a one-shot data migration command under `website/management/commands/`, decide whether it belongs in this startup sequence.

### Image handling

`image_cropping` + `easy_thumbnails` work together: cropping defines the crop box (stored as an `"x1,y1,x2,y2"` string by `ImageRatioField`), easy_thumbnails generates sized variants. `THUMBNAIL_PROCESSORS` is configured so `crop_corners` runs before the default chain, applying the stored box to any `{% thumbnail … box=obj.cropping %}` render. Image processing requires ImageMagick (installed in the Dockerfile) and a custom `imagemagick-policy.xml` is mounted into `/etc/ImageMagick-6/policy.xml` to enable PDF processing (see issue #974).

**`image_cropping` is an in-repo fork**, not the PyPI `django-image-cropping` (which was EOL Jcrop+jQuery, Django ≤4.0). Like `sortedm2m_filter_horizontal_widget`, the top-level `image_cropping/` package is project source code and shadows/replaces the dropped dependency. Its admin widget is **Cropper.js** (vendored static, no build step): editors preview and crop client-side *before* the first save (#1299/#1269). The data layer is intentionally unchanged — `ImageRatioField` is still a `CharField` whose `deconstruct()` returns `image_cropping.fields.ImageRatioField`, so the gitignored per-environment migrations that `import image_cropping.fields` keep working and the DB column is untouched (a regression test pins this path). See `image_cropping/README.md`. To bump Cropper.js, replace the vendored `static/image_cropping/cropper.min.{js,css}` (stay on the v1.x API; v2 is a different API).

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
- **Django template comments — `{# … #}` is SINGLE-LINE ONLY.** A `{# … #}` that
  spans multiple lines is NOT parsed as a comment; Django renders the whole thing
  (text and `#}` included) as visible page content. For any multi-line comment use
  `{% comment %} … {% endcomment %}`. This is a recurring footgun (it shipped to
  prod once as a comment printed on every award card, fixed in 2.14.2) — when
  adding or editing a `{# … #}`, confirm it stays on one line.
- Prefer clarity over cleverness; mark placeholders and TODOs clearly.

## Pull request conventions (from CONTRIBUTING.md)

- One issue per branch; branch name starts with the issue number, e.g. `335-adding-hover-to-landing-page`.
- UI changes require before/after screenshots or mockups in the PR (see issue #287 as a reference).
- Run the Pa11y a11y service before submitting any UI change.
- PRs target `master`.

## Issue conventions (labeling)

**Always apply labels when filing a GitHub issue via Claude Code** (`gh issue create --label ...`). Pick from the existing taxonomy below — most issues warrant 2–4 labels (typically one *kind* + one or more *areas*). Run `gh label list` to see the current set before creating new ones; only add a new label when nothing existing fits, and keep names/casing consistent with what's there.

The taxonomy (as of June 2026):

- **Kind:** `Bug`, `New Feature`, `Maintenance`, `Code Cleanup`, `Data Entry`, `Discuss`, `Won't Fix`, `Dependencies`, `Security`
- **Priority** (optional, maintainer's call — don't guess): `Priority: Very High` / `High` / `Medium` / `Low`
- **Effort** (optional): `Easy Fix`, `Time Consuming`
- **Backend / infra:** `Backend`, `Docker`, `Logging`, `Server Start Scripts`, `Django Upgrade`, `Testing / Test Harness`, `Rest API`, `Requires Updating Model Database`, `Needs UW CSE IT`
- **Frontend / UI:** `UI Design`, `CSS`, `Mobile`, `Accessibility`, `Navbar`, `Menu Bar`, `Footer`, `Banner`
- **Content areas / pages:** `Publications`, `Talks`, `Posters`, `Videos`, `Projects`, `Project Gallery Page`, `People`, `Member Page`, `News`, `Awards`, `Landing Page`, `FAQ Page`, `Admin`, `Sponsors`, `Grants & Funding`, `SEO`
- **Status:** `FixedNeedsToBeTestedOnTestServer`

Notes: `Awards` is for external recognitions and award content/data work; paper-level awards live on `Publication.award` (see Key model relationships) but issues about them still get `Awards` + `Publications`. Use `Grants & Funding` for proposals/funding-source tracking; `Sponsors` for sponsor logos/listings. Add `Requires Updating Model Database` whenever the work implies a schema/model change.
