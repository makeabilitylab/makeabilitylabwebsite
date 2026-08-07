# Database backups and restore

How the Makeability Lab website's data is backed up, how to check that it's
actually happening, and how to restore it. See issue
[#1443](https://github.com/makeabilitylab/makeabilitylabwebsite/issues/1443).

**Read the [Restoring](#restoring) section before you need it.** The one step
people get wrong under pressure is documented there: Postgres will not
initialize into a non-empty data directory, and the dumps live *inside* that
directory.

## What is backed up, and by whom

| Data | Where it lives | How it's protected |
| --- | --- | --- |
| Uploaded media (PDFs, images) | `/cse/web/research/makelab/www[-test]/` on the shared CSE filesystem | CSE IT's standard snapshot schedule — hourly, weekly, monthly, plus off-site to UW's lolo service. Retained 1 year. Plain files, so a snapshot is always consistent. |
| Code and schema | git | GitHub |
| **Database contents** | the `db` container's named volume (`db-data` → `/var/lib/postgresql/data`) | Two tiers, below |

The database is the only piece that needs special handling, because a
filesystem-level snapshot of a **live** Postgres data directory is not
guaranteed to be transaction-consistent. Restoring one behaves like recovering
from a hard power cut — usually fine, occasionally not.

So there are two tiers:

| Tier | Cadence | Guarantee |
| --- | --- | --- |
| CSE IT's ZFS snapshot of the raw volume | hourly | *Probably* restorable. Postgres crash recovery is designed for exactly this case. |
| Our `pg_dump`, written **into** that volume | daily | Guaranteed consistent restore point. |

Because the dump lives inside the volume that gets snapshotted, every snapshot
automatically carries a known-good dump. A snapshot from six months ago contains
that day's dump, which is why in-volume retention only needs to be 14 days.

> **The dump cadence is the guaranteed worst-case RPO, and more snapshots don't
> improve it.** Every hourly snapshot taken between two dumps contains the *same*
> dump. Hourly snapshots give more copies of one restore point, not more restore
> points.

## How it works

A `db-backup` sidecar service in `docker-compose.yml` runs
[`scripts/pg_backup.sh`](../scripts/pg_backup.sh) once an hour. The script is a
single pass: if today's dump doesn't exist yet it makes one, prunes anything past
retention, and writes a status file.

- **Dumps:** `/var/lib/postgresql/data/pg_backups/makeability-YYYY-MM-DD.sql.gz`
  (UTC date, mode 0600).
- **Retention:** 14 days, but the newest dump is *never* pruned regardless of
  age — otherwise a backup that had been failing for longer than the retention
  window would end with pruning deleting the last good dump too.
- **Status:** `status.json` on a small shared volume that the website container
  mounts read-only.

Two things in the compose config are load-bearing and shouldn't be "simplified":

1. `entrypoint` is overridden. Left alone, the postgres image's own entrypoint
   would try to start a second database server on that `PGDATA`.
2. The scheduling loop lives in `docker-compose.yml`, not inside
   `pg_backup.sh`. `docker compose up -d` only recreates a container whose
   *config* changed, so a loop inside the bind-mounted script would keep running
   stale code after a deploy — and there's no shell access to restart it by hand.

## Checking that backups are actually running

Because the dumps sit in a Docker volume on a host nobody has a shell on — and
inside a `PGDATA` the website container can't even traverse — the status file is
the only way to observe this. Three places surface it:

- **`/version.json`** — `backup_ok`, `last_backup_at`, `backup_age_hours`,
  `backup_count`. No auth needed; use this for any external check.
- **Admin dashboard** — a superuser-only warning callout, shown *only* when
  backups are stale or failing.
- **Admin → Data Health** — a panel with last success, age, size, how many
  dumps are retained, and the last error.

"Stale" means the newest dump is more than 36 hours old (`BACKUP_STALE_AFTER_HOURS`).
That's 1.5× the daily cadence, so one missed run doesn't cry wolf but a second
consecutive one does.

## Restoring

### The gotcha, first

The dumps live at `pg_backups/` **inside** the Postgres data directory. `initdb`
refuses to initialize into a non-empty directory, so you cannot wipe the database
and leave the backups sitting there. **Copy the dump out of the volume first.**
This is pinned by a test in `scripts/test_backup_restore.sh` so the warning can't
silently go stale.

### Restoring locally (development, or verifying a dump)

```bash
# 1. Get the dump out of the volume and onto your machine.
docker compose -f docker-compose-local-dev.yml cp \
  db-backup:/var/lib/postgresql/data/pg_backups/makeability-2026-08-07.sql.gz .

# 2. Stop the stack and destroy the database volume.
docker compose -f docker-compose-local-dev.yml down
docker volume rm makeabilitylabwebsite_postgres-data

# 3. Bring just the database back up on a fresh, empty volume.
docker compose -f docker-compose-local-dev.yml up -d db

# 4. Restore.
gunzip -c makeability-2026-08-07.sql.gz | \
  docker compose -f docker-compose-local-dev.yml exec -T db \
    psql -v ON_ERROR_STOP=1 -U admin -d makeability

# 5. Start the site and confirm Django agrees the database is complete.
docker compose -f docker-compose-local-dev.yml up -d
docker compose -f docker-compose-local-dev.yml exec website python manage.py migrate --check
```

Step 5 is the real test. `migrate --check` exits non-zero if Django thinks
migrations are pending, which is how you'd catch a restore that brought back
tables but not the `django_migrations` table.

### Restoring production or test

**This requires someone with Docker access on the host** — `grabthar` for
production, `docker-test2` for test. The maintainer does not have that (see the
server access model in `CLAUDE.md`), so a production restore means opening a
ticket with UW CSE IT. Send them this section.

The steps are the same as above, against `docker-compose.yml` and the external
volume `makeabilitylabcswashingtonedu_postgres16-data`. Before destroying
anything:

1. **Copy the chosen dump somewhere off the volume first.** If the volume itself
   is the problem, ask CSE IT to recover the dump from a ZFS snapshot or from
   lolo instead — the dump inside a snapshot is exactly what this whole scheme
   exists to provide.
2. **Take a copy of the current broken volume before overwriting it.** A
   corrupt database still contains data; a hasty restore over the top of it
   destroys any chance of salvaging rows the dump predates.
3. Restore, then confirm via `/version.json` and by loading the site.

There's no ad-hoc "back up right now" button, deliberately — see the follow-up
note in #1443. If you need a fresh dump before something risky and you can't
reach the host, the practical options are to wait for the next pass or ask CSE
IT to run one.

## Testing the backups

Two harnesses, both self-contained and namespaced so they never touch your real
stack, database, or volumes. **An untested backup is not a backup** — run these
after any change to `pg_backup.sh` or the compose wiring.

```bash
# Mechanics: dump → destroy → restore, on a synthetic schema built to break a
# naive dump (unicode, embedded quotes and newlines, NULLs, binary columns,
# a 540 KB row, views, foreign keys, sequences). ~1 minute.
bash scripts/test_backup_restore.sh

# The real thing: builds the actual Makeability Lab schema with `migrate`, seeds
# through the ORM (sortedm2m through-tables, rich text), backs up, destroys the
# volume, restores, and asserts Django accepts the result — `migrate --check`
# and `manage.py check` both pass. Needs a built website image. ~3 minutes.
bash scripts/test_backup_restore_django.sh
```

The Django-side unit tests (status file parsing, staleness, failure reporting)
run in the normal suite:

```bash
python manage.py test website.tests.test_backup_status --settings=makeabilitylab.settings_test
```

## Security

The dumps contain personal data — `Person.email`, which is deliberately withheld
from the public API. They are written mode 0600 into a Docker volume.

**Never move a dump under `media/`, `static/`, or any other web-served path.**
Everything under those is publicly downloadable. The status file is safe to
surface in the admin because it carries no row data.

## Configuration

Set on the `db-backup` service in `docker-compose.yml`:

| Variable | Default | Meaning |
| --- | --- | --- |
| `BACKUP_RETENTION_DAYS` | 14 | Delete dumps older than this (never the newest). |
| `BACKUP_MIN_KEEP` | 1 | Dumps always kept regardless of age. |
| `BACKUP_POLL_SECONDS` | 3600 | Time between passes. |
| `BACKUP_RETRY_SECONDS` | 300 | Time between passes after a failure. |

Django-side, in `settings.py`:

| Setting | Default | Meaning |
| --- | --- | --- |
| `BACKUP_STATUS_FILE` | `/var/backup-status/status.json` | Where to read status from (`ML_BACKUP_STATUS_FILE`). |
| `BACKUP_STALE_AFTER_HOURS` | 36 | Age at which the dashboard warns (`ML_BACKUP_STALE_AFTER_HOURS`). |
