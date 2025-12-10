# Deployment Guide

This document covers the Makeability Lab website's production infrastructure, deployment pipeline, and server administration.

## Table of Contents

- [Deployment Guide](#deployment-guide)
  - [Table of Contents](#table-of-contents)
  - [Server Overview](#server-overview)
  - [Deployment Pipeline](#deployment-pipeline)
    - [Deploying to Test](#deploying-to-test)
    - [Deploying to Production](#deploying-to-production)
    - [Verifying Deployment](#verifying-deployment)
  - [Versioning](#versioning)
    - [Creating a Release](#creating-a-release)
  - [Server Configuration](#server-configuration)
    - [Configuration File](#configuration-file)
    - [Environment Variables](#environment-variables)
  - [Debugging \& Logging](#debugging--logging)
    - [Log Files](#log-files)
    - [Accessing Logs via Web](#accessing-logs-via-web)
    - [Accessing Logs via SSH](#accessing-logs-via-ssh)
    - [Windows Network Drive Access](#windows-network-drive-access)
  - [Data Management](#data-management)
    - [Uploaded Files](#uploaded-files)
    - [Database Access](#database-access)
  - [Server Architecture Summary](#server-architecture-summary)

## Server Overview

The Makeability Lab website runs on two UW CSE servers:

| Server | URL | Purpose |
|--------|-----|---------|
| **Test** | https://makeabilitylab-test.cs.washington.edu | Staging environment for testing changes |
| **Production** | https://makeabilitylab.cs.washington.edu | Live public-facing website |

Each server has its own:
- PostgreSQL database
- File storage backend
- Log files

> **Important:** Content added to the test server does **not** affect production, and vice versa. They are completely independent environments.

## Deployment Pipeline

Deployments are automated via GitHub webhooks:

```
┌─────────────┐      ┌─────────────────┐      ┌─────────────────────┐
│ Push to     │ ───► │ Webhook fires   │ ───► │ makeabilitylab-test │
│ master      │      │                 │      │ auto-deploys        │
└─────────────┘      └─────────────────┘      └─────────────────────┘

┌─────────────┐      ┌─────────────────┐      ┌─────────────────────┐
│ Push a tag  │ ───► │ Webhook fires   │ ───► │ makeabilitylab      │
│ (e.g. 2.1.0)│      │                 │      │ (production)        │
└─────────────┘      └─────────────────┘      └─────────────────────┘
```

### Deploying to Test

Any push to `master` automatically deploys to the test server:

```bash
git push origin master
```

### Deploying to Production

Production deployments require a version tag:

```bash
git tag 2.1.0
git push --tags
```

### Verifying Deployment

Check the build log to confirm deployment succeeded:

- **Test:** https://makeabilitylab-test.cs.washington.edu/logs/buildlog.txt
- **Production:** https://makeabilitylab.cs.washington.edu/logs/buildlog.txt

## Versioning

We use [Semantic Versioning](https://semver.org/) for production releases.

| Change Type | Version Component | Example |
|-------------|-------------------|---------|
| **First release** | Start at 1.0.0 | `1.0.0` |
| **Bug fixes**, minor patches | Increment PATCH (third digit) | `1.0.0` → `1.0.1` |
| **New features** (backward compatible) | Increment MINOR (second digit) | `1.0.1` → `1.1.0` |
| **Breaking changes** | Increment MAJOR (first digit) | `1.1.0` → `2.0.0` |

View current and past versions on the [Releases page](https://github.com/makeabilitylab/makeabilitylabwebsite/releases).

### Creating a Release

1. Ensure all changes are merged to `master` and tested on the test server
2. Determine the appropriate version number based on the changes
3. Create and push the tag:

   ```bash
   git tag 2.1.0
   git push --tags
   ```

4. Verify deployment via the [production build log](https://makeabilitylab.cs.washington.edu/logs/buildlog.txt)

## Server Configuration

The production server was configured by UW CSE's IT team (Jason Howe).

### Configuration File

Django reads database credentials and secret keys from `config.ini`. This file:
- Is **not** stored in Git (for security)
- Is mounted as a Docker volume on the production server
- Contains PostgreSQL connection strings and Django secret keys

### Environment Variables

Production-specific settings are configured in `settings.py` using values from `config.ini`. Local development uses different defaults specified in `docker-compose-local-dev.yml`.

## Debugging & Logging

### Log Files

Logs are available via SSH or the web:

| Log | Description |
|-----|-------------|
| `debug.log` | Django application logs |
| `buildlog.txt` | Deployment build output |
| `httpd-access.log` | HTTP request logs |
| `httpd-error.log` | HTTP error logs |

### Accessing Logs via Web

- **Test:** https://makeabilitylab-test.cs.washington.edu/logs/
- **Production:** https://makeabilitylab.cs.washington.edu/logs/

### Accessing Logs via SSH

1. SSH into the server:

   ```bash
   ssh recycle.cs.washington.edu
   ```

2. Navigate to the log directory:

   ```bash
   # Test server
   cd /cse/web/research/makelab/www-test

   # Production server
   cd /cse/web/research/makelab/www
   ```

3. View recent log entries:

   ```bash
   # Last 100 lines
   tail -n 100 debug.log

   # Save to file
   tail -n 100 debug.log > last100lines.log

   # Follow log in real-time
   tail -f debug.log
   ```

### Windows Network Drive Access

If you have Windows directory mapping configured, logs are accessible at:

```
O:\cse\web\research\makelab\www        # Production
O:\cse\web\research\makelab\www-test   # Test
```

## Data Management

### Uploaded Files

Files uploaded via the Django admin (publications, talks, images, etc.) are stored in the `/media` folder:

| Server | Path |
|--------|------|
| Test | `/cse/web/research/makelab/www-test/media` |
| Production | `/cse/web/research/makelab/www/media` |

To browse uploaded files:

```bash
ssh recycle.cs.washington.edu
cd /cse/web/research/makelab/www/media  # or www-test for test server
ls -la
```

### Database Access

The production PostgreSQL database runs on `grabthar.cs.washington.edu`.

> **Note:** Direct database access is rarely needed. In the uncommon case you need to query PostgreSQL directly, you must connect through `recycle.cs.washington.edu`:

```bash
ssh recycle.cs.washington.edu
# Then connect to PostgreSQL from there
```

For routine data management, use the Django admin interface instead.

## Server Architecture Summary

```
┌────────────────────────────────────────────────────────────────┐
│                        GitHub                                  │
│                    (makeabilitylab/makeabilitylabwebsite)      │
└───────────────────────────┬────────────────────────────────────┘
                            │ webhooks
              ┌─────────────┴─────────────┐
              ▼                           ▼
┌─────────────────────────┐   ┌─────────────────────────┐
│   makeabilitylab-test   │   │    makeabilitylab       │
│   (push to master)      │   │    (push tags)          │
├─────────────────────────┤   ├─────────────────────────┤
│ Docker container        │   │ Docker container        │
│ PostgreSQL (local)      │   │ PostgreSQL (grabthar)   │
│ Media: www-test/media   │   │ Media: www/media        │
└─────────────────────────┘   └─────────────────────────┘
```