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
  - [Shutting Down](#shutting-down)
  - [Creating a Superuser](#creating-a-superuser)
  - [Adding Content](#adding-content)
  - [Development Workflow](#development-workflow)
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

## Pull Request Guidelines

- **UI changes require mockups**: Include before/after screenshots or design mockups so we can collectively agree on the visual direction. See [issue #287](https://github.com/makeabilitylab/makeabilitylabwebsite/issues/287) for a good example.

- **One issue per branch**: Keep PRs focused on a single issue for easier review.

- **Test locally**: Verify your changes work before submitting.

- **Clear descriptions**: Explain what changed and why in your PR description.

## Troubleshooting

See our [Troubleshooting Wiki](https://github.com/makeabilitylab/makeabilitylabwebsite/wiki/Troubleshooting) for common issues and solutions.
