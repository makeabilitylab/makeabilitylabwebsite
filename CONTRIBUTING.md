# Contributing to the Makeability Lab Website

This document outlines how to set up your local development environment and our process for submitting changes.

## Table of Contents

- [Contributing to the Makeability Lab Website](#contributing-to-the-makeability-lab-website)
  - [Table of Contents](#table-of-contents)
  - [Prerequisites](#prerequisites)
  - [Docker Installation](#docker-installation)
    - [MacOS](#macos)
    - [Windows (WSL2)](#windows-wsl2)
  - [Running the Website](#running-the-website)
  - [Opening the Project in VSCode (WSL2)](#opening-the-project-in-vscode-wsl2)
    - [Prerequisites](#prerequisites-1)
    - [Option 1: Open in the Dev Container (Recommended)](#option-1-open-in-the-dev-container-recommended)
    - [Option 2: Edit on the WSL2 Filesystem (Lightweight Alternative)](#option-2-edit-on-the-wsl2-filesystem-lightweight-alternative)
  - [Shutting Down](#shutting-down)
  - [Creating a Superuser](#creating-a-superuser)
  - [Adding Content](#adding-content)
  - [Development Workflow](#development-workflow)
  - [Running the Test Suite](#running-the-test-suite)
    - [When to add a test](#when-to-add-a-test)
    - [Troubleshooting](#troubleshooting-tests)
  - [Accessibility Testing](#accessibility-testing)
    - [Running Accessibility Checks](#running-accessibility-checks)
    - [Configuring Tests](#configuring-tests)
  - [Pull Request Guidelines](#pull-request-guidelines)
  - [Troubleshooting](#troubleshooting)

## Prerequisites

* [Git](https://git-scm.com/)
* [Docker Desktop](https://www.docker.com/get-started)

## Docker Installation

### MacOS

1.  **Install Docker:** Download and install [Docker Desktop](https://www.docker.com/get-started). Run `docker version` in your terminal to verify it is running.
2.  **Clone the Repository:**
    ```bash
    git clone https://github.com/jonfroehlich/makeabilitylabwebsite.git
    cd makeabilitylabwebsite
    ```
3.  **Build the Image:**
    ```bash
    docker build . -t makelab_image
    ```
    *Note: This may take 2-3 minutes.*
4.  **Run the Container:**
    ```bash
    docker-compose -f docker-compose-local-dev.yml up
    ```
    To run in detached mode (background), add the `-d` flag: `docker-compose -f docker-compose-local-dev.yml up -d`.
5. Don't forget to create a local superuser to create content (see below).

### Windows (WSL2)

If you dev on Windows, you should use [WSL2](https://docs.microsoft.com/en-us/windows/wsl/install) for better performance and Linux kernel compatibility.

1.  **Install WSL2**
    * Follow the [WSL2 installation guide](https://learn.microsoft.com/en-us/windows/wsl/install)
2.  **Install Docker:**
    * Install [Docker Desktop for Windows](https://docs.docker.com/desktop/windows/install/).
    * Enable "Use the WSL 2 based engine" in Docker Settings > General.
    * Under **Resources > WSL Integration**, enable integration for your Linux distro (e.g., Ubuntu).
3.  **Clone the Repository (Inside WSL):**
    Open your Linux shell and run:
    ```bash
    git clone https://github.com/makeabilitylab/makeabilitylabwebsite.git
    cd makeabilitylabwebsite
    ```
4.  **Set Permissions:**
    Run the following to ensure Docker can execute scripts and write to folders:
    ```bash
    chmod 755 docker-entrypoint.sh
    chmod 777 media
    mkdir -p static && chmod -R 777 static/
    mkdir -p website/migrations && chmod -R 777 website/
    ```
5.  **Build and Run:**
    ```bash
    docker build . -t makelab_image
    docker-compose -f docker-compose-local-dev.yml up
    ```
6. **(Optional) Map WSL filesystem to Windows**

   Press `Win + R`, type `\\wsl$`, find your Linux distro folder, right-click → **Map Network Drive**. This lets you browse Linux files from Windows Explorer.

7. Don't forget to create a local superuser to create content (see below).

## Running the Website

After initial setup, start the development server with:

```bash
docker-compose -f docker-compose-local-dev.yml up
```

Or use the convenience script:

```bash
./run-docker-local-dev.sh
```

The site will be available at [http://localhost:8571](http://localhost:8571).

> **Note:** You don't need to rebuild the image unless you modify `Dockerfile` or `docker-compose.yml`. Code changes are reflected automatically.

## Opening the Project in VSCode (WSL2)

> **Why launch from WSL matters:** On Windows, your code lives inside the WSL2 Linux filesystem, but VSCode runs on Windows. If you open the project from Windows Explorer or via `\\wsl$`, VSCode reads files across the Windows↔Linux boundary, which is slow and can silently break file watching (so live reload may not fire). The fix is to launch VSCode *from inside WSL2* so its backend runs on the Linux side, right next to your code.

This repo ships a **Dev Container** config (`.devcontainer/devcontainer.json`), so VSCode can open the project *inside* the running website container with Python IntelliSense, Django syntax highlighting, and template formatting all preconfigured. **This is the recommended workflow** (Option 1 below). Option 2 is a lighter-weight alternative for quick edits when you don't need container-aware IntelliSense.

### Prerequisites

Install these two VSCode extensions (VSCode usually prompts you for the WSL one automatically the first time you run `code .` from WSL):

* **WSL** (`ms-vscode-remote.remote-wsl`) — runs VSCode's backend inside your WSL2 distro.
* **Dev Containers** (`ms-vscode-remote.remote-containers`) — lets VSCode open/reopen the project inside the Docker container.

You do **not** need to install Python, Pylance, the Django extension, or djlint yourself—the Dev Container installs them automatically *inside the container* (see below).

### Option 1: Open in the Dev Container (Recommended)

This runs VSCode's backend inside the `website` container, so the integrated terminal, Python interpreter, debugger, and IntelliSense all use the container's exact environment and installed packages.

1. **Open a WSL2 terminal** and navigate to the repo where you cloned it *inside* WSL (somewhere under your Linux home like `~/`, **not** under `/mnt/c/...`):

   ```bash
   cd makeabilitylabwebsite
   ```

2. **Launch VSCode from WSL:**

   ```bash
   code .
   ```

   Confirm the green badge in the **bottom-left corner** reads **`WSL: Ubuntu`** (or your distro's name). If it doesn't, you've opened the Windows-side copy—close the window and re-run `code .` from the WSL shell.

3. **Reopen in the container.** VSCode detects `.devcontainer/devcontainer.json` and pops a notification: **"Reopen in Container."** Click it. (Missed the popup? Open the Command Palette with `Ctrl+Shift+P` and run **Dev Containers: Reopen in Container**.)

4. VSCode now starts the `website` service (and the `db` it depends on) from `docker-compose-local-dev.yml`, opens `/code` as the workspace, and **on first creation** automatically:
   * installs Pylance, the Django extension (`batisteo.vscode-django`), and djlint *inside the container*;
   * sets djlint as the formatter for Django/HTML templates;
   * runs `git config --global --add safe.directory /code` to prevent the Git "dubious ownership" error.

5. The site comes up at [http://localhost:8571](http://localhost:8571) as usual. Edits reflect live (the project is mounted at `/code`), and IntelliSense now resolves against the container's Python.

> **Tip:** To switch back to plain host-side editing, run **Dev Containers: Reopen Folder Locally** from the Command Palette. To re-enter the container later, it's **Dev Containers: Reopen in Container** again.

### Option 2: Edit on the WSL2 Filesystem (Lightweight Alternative)

Skip the container and edit directly on the WSL2 side. Faster to open, but VSCode uses your **WSL2 host's** Python, so IntelliSense won't see packages installed only inside the container.

1. From a WSL2 terminal in the repo, run `code .` (confirm the `WSL: Ubuntu` badge as above) and **dismiss** the "Reopen in Container" prompt.

2. Start the site from VSCode's integrated terminal:

   ```bash
   docker-compose -f docker-compose-local-dev.yml up
   ```

3. Visit [http://localhost:8571](http://localhost:8571). Because the project is mounted into the container (`.:/code`), your edits are reflected immediately—no rebuild required.

> **Tip:** To get a plain shell inside the running container (e.g., to run `manage.py` commands) without using the Dev Container, use:
> ```bash
> docker exec -it makeabilitylabwebsite-website-1 bash
> ```
> Depending on your Docker Compose version the name may use underscores: `makeabilitylabwebsite_website_1`. This is the same container referenced in [Creating a Superuser](#creating-a-superuser).

## Shutting Down

To stop the containers:

```bash
docker-compose down
```

**Important:** Without this command, containers persist in the background even after closing your terminal, keeping port 8571 occupied.

## Creating a Superuser

A superuser account is required to access the Django admin interface and add content.

1. With containers running, open a new terminal

2. Access the website container:

   ```bash
   docker exec -it makeabilitylabwebsite_website_1 bash
   ```

   > **Note:** Depending on your Docker/Compose version, the container name may use a hyphen instead of underscore: `makeabilitylabwebsite-website-1`

3. Create the superuser:

   ```bash
   python manage.py createsuperuser
   ```

4. Follow the prompts to set username, email, and password

5. Exit the container:

   ```bash
   exit
   ```
## Adding Content

1. Navigate to the Django admin interface: [http://localhost:8571/admin](http://localhost:8571/admin)

2. Log in with your superuser credentials

3. Under the **WEBSITE** header, select the content type you want to add (Publications, People, Projects, etc.)

4. Click **ADD** in the upper right corner

5. Fill in the required fields and save

> **Tip:** Only add content needed for the issue you're working on—this saves time during development.

## Development Workflow

1. **Find or create an issue**

   Browse [existing issues](https://github.com/makeabilitylab/makeabilitylabwebsite/issues) or create a new one. Assign yourself to the issue you'll work on.

2. **Create a feature branch**

   Branch names should be descriptive and reference the issue:

   ```bash
   git checkout -b 335-adding-hover-to-landing-page  # for issue #335
   ```

   Each branch should address a single issue.

3. **Make your changes**

   Write code, test locally, and commit with clear messages.

4. **Submit a pull request**

   Push your branch and open a PR against `master`. PRs undergo code review and local testing before merging.

## Running the Test Suite

The Python test suite lives in `website/tests.py` and runs inside the website container:

```bash
docker exec makeabilitylabwebsite-website-1 python manage.py test website
```

The suite has two complementary styles:

| Style | Base class | What it's for |
|---|---|---|
| **Unit** | `SimpleTestCase` + `MagicMock` | Pure logic — formatters, BibTeX generation, single-method behavior. No DB; runs in milliseconds. |
| **Integration** | `DatabaseTestCase` (subclass of Django's `TestCase`) | View, queryset, template, and URL-routing regressions. Each test runs inside a transaction that is rolled back, so tests stay isolated. |

The `DatabaseTestCase` base provides `make_person`, `make_publication`, and `make_news_item` helpers built on plain `Model.objects.create()` — use those rather than hand-rolling fixtures.

### When to add a test

When you fix a bug that's reachable through a real queryset, URL, view, or template, add a regression test **before** applying the fix. The point is to pin behavior so the bug can't quietly re-emerge later. The existing tests show the pattern:

- `NewsItemNullAuthorViewTests` — view-level regression for a null-FK that crashed `/news/<id>/`
- `PublicationsViewQueryCountTests` — query-count regression that pins the `prefetch_related` batch on `/publications/`
- `BibtexCitationTests` / `FormattedForumNameTests` — pure-logic regressions for publication-formatting bugs

If a fix is genuinely not unit-testable (FD leaks, `super().save()`-dependent paths), say so explicitly in the commit body rather than writing a brittle test or skipping silently.

### Troubleshooting tests

`website/migrations/` is **gitignored** — each environment (your laptop, test, production) maintains its own migration history on disk. This sometimes drifts. If `manage.py test` fails at test-DB creation, the symptoms and fixes are:

- **`database "test_makeability" already exists`** — a prior failed run left it half-built. Drop and retry:
  ```bash
  docker exec makeabilitylabwebsite-db-1 psql -U admin -d postgres -c "DROP DATABASE IF EXISTS test_makeability;"
  ```
- **`column "..." of relation "..." already exists`** — a local migration file duplicates a field that a later `0001_initial` regeneration already includes. Same fix (drop the test DB) usually clears it; if it persists, the offending migration is a local stale artifact that needs to be edited or removed. See [#1267](https://github.com/makeabilitylab/makeabilitylabwebsite/issues/1267) for the durable fix (test-only settings shim using `MIGRATION_MODULES`).

## Accessibility Testing

We use [Pa11y CI](https://github.com/pa11y/pa11y-ci) with the [Axe](https://www.deque.com/axe/) engine to run automated accessibility checks against the local site. Tests are configured in `.pa11yci.json` and target WCAG 2.0 AA compliance.

### Running Accessibility Checks

Make sure the website is running first, then run the a11y service:
```bash
# Start the website (if not already running)
docker-compose -f docker-compose-local-dev.yml up -d

# Run accessibility checks
docker-compose -f docker-compose-local-dev.yml --profile testing run --rm a11y
```

To generate a JSON report:
```bash
docker-compose -f docker-compose-local-dev.yml --profile testing run --rm a11y sh -c "
  npm install -g pa11y-ci &&
  pa11y-ci --config /workspace/.pa11yci.json --json | tee /workspace/a11y-report.json
"
```

### Configuring Tests

Edit `.pa11yci.json` to add or remove URLs to test. The `urls` array lists every page that will be checked.

## Pull Request Guidelines

- **UI changes require mockups**: Include before/after screenshots or design mockups so we can collectively agree on the visual direction. See [issue #287](https://github.com/makeabilitylab/makeabilitylabwebsite/issues/287) for a good example.

- **One issue per branch**: Keep PRs focused on a single issue for easier review.

- **Run the test suite**: `docker exec makeabilitylabwebsite-website-1 python manage.py test website` should pass before opening a PR. If your fix is reachable through a real queryset, view, or template, add a regression test (see [Running the Test Suite](#running-the-test-suite)).

- **Test locally**: Verify your changes work in the browser before submitting.

- **Run accessibility checks**: Run the a11y service before submitting UI changes to catch WCAG violations early.

- **Clear descriptions**: Explain what changed and why in your PR description.

## Troubleshooting

See our [Troubleshooting Wiki](https://github.com/makeabilitylab/makeabilitylabwebsite/wiki/Troubleshooting) for common issues and solutions.