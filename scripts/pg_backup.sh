#!/bin/bash
#
# One backup pass for the Makeability Lab database (#1443).
#
# Writes a dated, gzipped pg_dump into a subdirectory of the postgres data
# volume so that CSE IT's volume-level ZFS snapshots always contain a
# transaction-consistent restore point. A filesystem snapshot of a *live*
# PGDATA is only probably restorable (it looks like a power cut to postgres);
# this dump is the guaranteed tier. See docs/BACKUPS.md.
#
# This script deliberately performs a SINGLE pass and exits. The scheduling
# loop lives in docker-compose.yml instead, because `docker compose up -d`
# only recreates a container whose *config* changed: if the loop lived here,
# in this bind-mounted file, edits to the backup logic would never take effect
# on a running server (and there is no shell access to restart it by hand).
# Re-invoking the script each pass means logic changes deploy normally.
#
# Runs as root, which is needed to write the shared status volume: Docker
# creates named-volume roots as root:root, so an unprivileged uid could not
# create files there. The container's only job is to run pg_dump over the
# stack's private network.
#
# Environment:
#   PGHOST/PGUSER/PGPASSWORD/PGDATABASE  standard libpq connection settings
#   BACKUP_DIR             where dumps are written (default: inside PGDATA)
#   STATUS_DIR             where status.json is written for Django to read
#   BACKUP_RETENTION_DAYS  delete dumps older than this (default 14)
#   BACKUP_MIN_KEEP        never prune below this many dumps (default 1)
#
# Usage (one pass, as run by the db-backup service):
#   bash /backup-scripts/pg_backup.sh

# No `set -e`: a failed dump must still fall through to write a status file
# recording the failure, otherwise a broken backup is indistinguishable from
# one that has simply not run yet. pipefail is required so that a pg_dump
# failure is not masked by gzip's success.
set -uo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/lib/postgresql/data/pg_backups}"
STATUS_DIR="${STATUS_DIR:-/var/backup-status}"
STATUS_FILE="$STATUS_DIR/status.json"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
MIN_KEEP="${BACKUP_MIN_KEEP:-1}"
DB_NAME="${PGDATABASE:-makeability}"

# Dumps contain personal data (Person.email, which is deliberately withheld
# from the public API), so they are created mode 0600. They live in a Docker
# volume, never under a web-served path.
umask 077

now_iso() { date -u +%Y-%m-%dT%H:%M:%SZ; }

# Escape a string for embedding in a JSON string literal, and collapse it to a
# single line. Only used for error text, which is untrusted-ish (stderr from
# pg_dump) and must not be able to corrupt the status file's JSON.
json_escape() {
  printf '%s' "$1" | tr '\n\r\t' '   ' \
    | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' | cut -c1-500
}

file_mtime_iso() { date -u -d "@$(stat -c %Y "$1")" +%Y-%m-%dT%H:%M:%SZ; }

# ---------------------------------------------------------------------------
# Write status.json atomically (temp file + rename) so Django never reads a
# half-written file. Mode 0644 because the website container reads it as a
# different uid (48/apache) than this one.
# ---------------------------------------------------------------------------
write_status() {
  local ok="$1" error="$2"
  local last_at='null' last_file='null' last_bytes='null'
  local oldest_at='null' count=0
  local newest oldest

  newest="$(find "$BACKUP_DIR" -maxdepth 1 -type f -name '*.sql.gz' -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -n 1 | cut -d' ' -f2-)"
  oldest="$(find "$BACKUP_DIR" -maxdepth 1 -type f -name '*.sql.gz' -printf '%T@ %p\n' 2>/dev/null | sort -n  | head -n 1 | cut -d' ' -f2-)"
  count="$(find "$BACKUP_DIR" -maxdepth 1 -type f -name '*.sql.gz' 2>/dev/null | wc -l)"

  if [ -n "$newest" ]; then
    last_at="\"$(file_mtime_iso "$newest")\""
    last_file="\"$(json_escape "$(basename "$newest")")\""
    last_bytes="$(stat -c %s "$newest")"
  fi
  if [ -n "$oldest" ]; then
    oldest_at="\"$(file_mtime_iso "$oldest")\""
  fi

  local error_json='null'
  if [ -n "$error" ]; then
    error_json="\"$(json_escape "$error")\""
  fi

  mkdir -p "$STATUS_DIR"
  local tmp="$STATUS_FILE.tmp"
  cat > "$tmp" <<EOF
{
  "schema_version": 1,
  "database": "$(json_escape "$DB_NAME")",
  "last_attempt_at": "$(now_iso)",
  "last_attempt_ok": $ok,
  "error": $error_json,
  "last_backup_at": $last_at,
  "last_backup_file": $last_file,
  "last_backup_bytes": $last_bytes,
  "oldest_backup_at": $oldest_at,
  "backup_count": $count,
  "retention_days": $RETENTION_DAYS
}
EOF
  chmod 0644 "$tmp"
  mv -f "$tmp" "$STATUS_FILE"
  chmod 0755 "$STATUS_DIR"
}

# ---------------------------------------------------------------------------
# Prune dumps past the retention window.
#
# Retention is deliberately short (14 days) because CSE IT keeps volume
# snapshots for a year, so a snapshot from months ago still carries that day's
# dump. In-volume retention only has to cover the recent window.
#
# The newest MIN_KEEP dumps are never pruned regardless of age. Without that
# guard, a dump that has been failing for longer than the retention window
# would end with pruning deleting the last good dump too — turning one broken
# backup into total loss of app-level restore points.
# ---------------------------------------------------------------------------
prune_old_backups() {
  local keep_args=() file
  while IFS= read -r file; do
    [ -n "$file" ] && keep_args+=(! -path "$file")
  done < <(find "$BACKUP_DIR" -maxdepth 1 -type f -name '*.sql.gz' -printf '%T@ %p\n' 2>/dev/null \
             | sort -rn | head -n "$MIN_KEEP" | cut -d' ' -f2-)

  find "$BACKUP_DIR" -maxdepth 1 -type f -name '*.sql.gz' \
       -mtime "+$RETENTION_DAYS" "${keep_args[@]}" -delete 2>/dev/null
}

# ---------------------------------------------------------------------------
# Main pass
# ---------------------------------------------------------------------------
if ! mkdir -p "$BACKUP_DIR"; then
  # Can't even reach the volume; still try to report it.
  write_status false "Could not create backup directory $BACKUP_DIR"
  exit 1
fi
chmod 0700 "$BACKUP_DIR"

# UTC date, so the rollover point does not shift with daylight saving. Note
# this means the file named for a given day rolls over at 5pm/4pm Pacific.
target="$BACKUP_DIR/${DB_NAME}-$(date -u +%F).sql.gz"

if [ -f "$target" ]; then
  # Today's dump already exists. Still prune and refresh status so a running
  # container keeps its status file current between dumps.
  prune_old_backups
  write_status true ""
  exit 0
fi

tmp_target="$target.partial"
err_file="$(mktemp)"

# --no-owner/--no-privileges keep the dump restorable into a database owned by
# a differently-named role. There is no separate pg_dumpall for globals: the
# only role is the one POSTGRES_USER recreates on any fresh container.
pg_dump --no-owner --no-privileges "$DB_NAME" 2>"$err_file" | gzip -c > "$tmp_target"
dump_status=$?

if [ "$dump_status" -ne 0 ]; then
  rm -f "$tmp_target"
  write_status false "pg_dump failed (exit $dump_status): $(cat "$err_file")"
  rm -f "$err_file"
  exit 1
fi

# Catch a truncated or corrupt archive before it is promoted to today's dump —
# otherwise a bad file would satisfy the "today already done" check above and
# suppress every retry until tomorrow.
if ! gzip -t "$tmp_target" 2>>"$err_file"; then
  rm -f "$tmp_target"
  write_status false "gzip integrity check failed: $(cat "$err_file")"
  rm -f "$err_file"
  exit 1
fi

# Promote atomically: a container killed mid-dump leaves only a .partial file,
# never something that looks like a finished backup.
mv -f "$tmp_target" "$target"
rm -f "$err_file"

prune_old_backups
write_status true ""
echo "Wrote $(basename "$target") ($(stat -c %s "$target") bytes)"
