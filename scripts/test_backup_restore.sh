#!/bin/bash
#
# End-to-end proof that scripts/pg_backup.sh produces a dump that actually
# restores (#1443). An untested backup is not a backup.
#
# This exercises the real disaster path, not a simulation of it:
#   1. stand up a throwaway postgres and seed it with awkward data
#   2. run the REAL scripts/pg_backup.sh against it
#   3. assert the dump and status file look right
#   4. copy the dump out, then DESTROY the container and its volume
#   5. bring up postgres on a genuinely fresh volume and restore
#   6. assert the restored database is byte-identical in content
#
# It also pins the initdb-refuses-a-non-empty-directory behavior that
# docs/BACKUPS.md warns about, so that caveat can't silently go stale.
#
# Everything is namespaced under mlbackuptest-* and torn down at the end, so
# this never touches the developer's real stack, database, or volumes.
#
# Usage:
#   bash scripts/test_backup_restore.sh
#
# Requires: docker, the postgres image used by the stack, and python3 on the
# host (used to parse status.json in the assertions below — everything
# postgres-specific runs inside a container, but that parsing does not).

set -uo pipefail

PROJECT=mlbackuptest
IMAGE="${POSTGRES_IMAGE:-postgres:16}"
NET="$PROJECT-net"
DATA_VOL="$PROJECT-data"
STATUS_VOL="$PROJECT-status"
DB_CONTAINER="$PROJECT-db"
DB_NAME=makeability
DB_USER=admin
DB_PASS=password

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Under /tmp specifically: Docker Desktop on macOS shares /tmp by default, and
# the rescued dump has to be bind-mountable back into a container.
WORK_DIR="$(mktemp -d /tmp/mlbackuptest.XXXXXX)"

PASS=0
FAIL=0

green() { printf '\033[32m%s\033[0m\n' "$1"; }
red()   { printf '\033[31m%s\033[0m\n' "$1"; }
step()  { printf '\n\033[1m== %s\033[0m\n' "$1"; }

ok()   { PASS=$((PASS+1)); green "  PASS  $1"; }
bad()  { FAIL=$((FAIL+1)); red   "  FAIL  $1"; }

assert_eq() {
  # assert_eq <label> <expected> <actual>
  if [ "$2" = "$3" ]; then ok "$1"; else bad "$1 (expected '$2', got '$3')"; fi
}

assert_true() {
  # assert_true <label> <command...>
  if "${@:2}" >/dev/null 2>&1; then ok "$1"; else bad "$1"; fi
}

# Docker teardown only. Kept separate from the temp-dir teardown because this
# also runs at startup to clear leftovers from an interrupted previous run —
# and at that point WORK_DIR is still needed.
cleanup_docker() {
  docker rm -f "$DB_CONTAINER" >/dev/null 2>&1
  docker volume rm -f "$DATA_VOL" "$STATUS_VOL" "$DATA_VOL-dirty" "$PROJECT-scratch" >/dev/null 2>&1
  docker network rm "$NET" >/dev/null 2>&1
}
cleanup() { cleanup_docker; rm -rf "$WORK_DIR"; }
trap cleanup EXIT

psql_db() { docker exec -i "$DB_CONTAINER" psql -v ON_ERROR_STOP=1 -U "$DB_USER" -d "$DB_NAME" "$@"; }

start_db() {
  # start_db <volume>. The alias matters: the backup container connects to
  # PGHOST=db, exactly as it does in docker-compose.yml.
  docker run -d --name "$DB_CONTAINER" --network "$NET" --network-alias db \
    -e POSTGRES_DB="$DB_NAME" -e POSTGRES_USER="$DB_USER" -e POSTGRES_PASSWORD="$DB_PASS" \
    -v "$1:/var/lib/postgresql/data" "$IMAGE" >/dev/null

  for _ in $(seq 1 60); do
    if docker exec "$DB_CONTAINER" pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; then
      # pg_isready goes true slightly before the init scripts finish; make sure
      # we can actually run a query before returning.
      if psql_db -c 'SELECT 1' >/dev/null 2>&1; then return 0; fi
    fi
    sleep 1
  done
  red "postgres did not become ready"; exit 1
}

run_backup_pass() {
  docker run --rm --network "$NET" \
    -e PGHOST=db -e PGUSER="$DB_USER" -e PGPASSWORD="$DB_PASS" -e PGDATABASE="$DB_NAME" \
    -e BACKUP_RETENTION_DAYS=14 \
    -v "$DATA_VOL:/var/lib/postgresql/data" \
    -v "$STATUS_VOL:/var/backup-status" \
    -v "$SCRIPT_DIR:/backup-scripts:ro" \
    "$IMAGE" bash /backup-scripts/pg_backup.sh
}

# Read a file out of a volume without needing a running container on it.
vol_cat() { docker run --rm -v "$1:/v" "$IMAGE" cat "/v/$2" 2>/dev/null; }
vol_ls()  { docker run --rm -v "$1:/v" "$IMAGE" sh -c "ls -1 /v/$2 2>/dev/null"; }

# ---------------------------------------------------------------------------
step "Setup: throwaway postgres on a private network"
# ---------------------------------------------------------------------------
cleanup_docker
docker network create "$NET" >/dev/null
start_db "$DATA_VOL"
green "  postgres up ($IMAGE)"

# ---------------------------------------------------------------------------
step "Seed data designed to break a naive dump"
# ---------------------------------------------------------------------------
psql_db >/dev/null <<'SQL'
CREATE TABLE person (
    id       serial PRIMARY KEY,
    name     text NOT NULL,
    email    text,
    bio      text,
    joined   timestamptz,
    headshot bytea
);

INSERT INTO person (name, email, bio, joined, headshot) VALUES
  ('Ada Lovelace',   'ada@example.edu',  'Wrote the first algorithm.', '2020-01-02 03:04:05+00', '\x89504e47'::bytea),
  ('Grace Hopper',   NULL,               NULL,                          NULL,                     NULL),
  ('José Ñuñez',     'jose@example.edu', 'Accents: é ü ñ — em dash',   '2021-06-07 08:09:10+00', NULL),
  ('张伟',            'zhang@example.edu','Unicode CJK name',            '2022-02-03 04:05:06+00', NULL),
  ('O''Brien, Pat',  'pat@example.edu',  'Single '' quote and "double"', '2023-03-04 05:06:07+00', NULL),
  ('Newline Nancy',  'nan@example.edu',  E'line one\nline two\ttabbed', '2024-04-05 06:07:08+00', NULL);

-- A wide row, to catch truncation that a handful of small rows would hide.
INSERT INTO person (name, bio) VALUES ('Big Bio', repeat('lorem ipsum dolor sit amet ', 20000));

CREATE TABLE publication (
    id       serial PRIMARY KEY,
    title    text NOT NULL,
    year     int,
    author_id int REFERENCES person(id)
);
INSERT INTO publication (title, year, author_id) VALUES
  ('Notes on the Analytical Engine', 1843, 1),
  ('A Compiler for COBOL',           1952, 2),
  ('Sidewalk Accessibility at Scale',2024, 3);

CREATE VIEW recent_publication AS SELECT * FROM publication WHERE year >= 2000;
SQL
green "  seeded 7 people, 3 publications, 1 view"

FINGERPRINT_SQL="SELECT (SELECT count(*) FROM person) || '/' || (SELECT count(*) FROM publication) || '/' || (SELECT md5(string_agg(p::text, '|' ORDER BY p.id)) FROM person p) || '/' || (SELECT md5(string_agg(q::text, '|' ORDER BY q.id)) FROM publication q)"
BEFORE_FP="$(psql_db -tAc "$FINGERPRINT_SQL")"
green "  fingerprint before: $BEFORE_FP"

# ---------------------------------------------------------------------------
step "Run the real scripts/pg_backup.sh"
# ---------------------------------------------------------------------------
BACKUP_OUTPUT="$(run_backup_pass 2>&1)"
BACKUP_RC=$?
echo "$BACKUP_OUTPUT" | sed 's/^/  /'
assert_eq "backup pass exits 0" "0" "$BACKUP_RC"

TODAY="$(date -u +%F)"
DUMP_NAME="$DB_NAME-$TODAY.sql.gz"
LISTING="$(vol_ls "$DATA_VOL" "pg_backups")"
if echo "$LISTING" | grep -qx "$DUMP_NAME"; then ok "dump $DUMP_NAME exists in the data volume"
else bad "dump $DUMP_NAME missing (saw: $LISTING)"; fi

if ! echo "$LISTING" | grep -q '\.partial$'; then ok "no leftover .partial file"
else bad "a .partial file was left behind"; fi

assert_true "dump passes gzip integrity check" \
  docker run --rm -v "$DATA_VOL:/v" "$IMAGE" gzip -t "/v/pg_backups/$DUMP_NAME"

DUMP_MODE="$(docker run --rm -v "$DATA_VOL:/v" "$IMAGE" stat -c %a "/v/pg_backups/$DUMP_NAME")"
assert_eq "dump is mode 600 (contains personal data)" "600" "$DUMP_MODE"

# ---------------------------------------------------------------------------
step "Status file"
# ---------------------------------------------------------------------------
# Always read the status through a file, never through a shell-interpolated
# string: the error field can contain quotes, and a harness that mangles them
# would be testing itself rather than the script.
refresh_status() { vol_cat "$STATUS_VOL" status.json > "$WORK_DIR/status.json"; }
status_field() { python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('$1'))" "$WORK_DIR/status.json"; }
status_is_json() { python3 -m json.tool "$WORK_DIR/status.json" >/dev/null 2>&1; }

refresh_status
sed 's/^/  /' "$WORK_DIR/status.json"

assert_true "status.json is valid JSON" status_is_json
assert_eq "status reports success"        "True"      "$(status_field last_attempt_ok)"
assert_eq "status reports no error"       "None"      "$(status_field error)"
assert_eq "status counts one backup"      "1"         "$(status_field backup_count)"
assert_eq "status names the dump"         "$DUMP_NAME" "$(status_field last_backup_file)"

STATUS_MODE="$(docker run --rm -v "$STATUS_VOL:/v" "$IMAGE" stat -c %a /v/status.json)"
assert_eq "status.json is world-readable (website container reads it as another uid)" "644" "$STATUS_MODE"

# ---------------------------------------------------------------------------
step "Second pass in the same day is a no-op, not a duplicate or an error"
# ---------------------------------------------------------------------------
FIRST_BYTES="$(status_field last_backup_bytes)"
run_backup_pass >/dev/null 2>&1
assert_eq "second pass still exits 0" "0" "$?"
refresh_status
assert_eq "still exactly one dump" "1" "$(status_field backup_count)"
assert_eq "dump was not rewritten" "$FIRST_BYTES" "$(status_field last_backup_bytes)"

# ---------------------------------------------------------------------------
step "A failing dump is reported as a failure, not as silence"
# ---------------------------------------------------------------------------
# Point the backup at a database that does not exist; the status file must flip
# to ok=false with an error. This is the case that would otherwise be
# indistinguishable from "hasn't run yet".
docker run --rm --network "$NET" \
  -e PGHOST=db -e PGUSER="$DB_USER" -e PGPASSWORD="$DB_PASS" -e PGDATABASE=nonexistent_db \
  -v "$DATA_VOL:/var/lib/postgresql/data" \
  -v "$STATUS_VOL:/var/backup-status" \
  -v "$SCRIPT_DIR:/backup-scripts:ro" \
  "$IMAGE" bash /backup-scripts/pg_backup.sh >/dev/null 2>&1
FAIL_RC=$?
assert_eq "failing pass exits non-zero" "1" "$FAIL_RC"
refresh_status
assert_eq "status flips to not-ok" "False" "$(status_field last_attempt_ok)"
if [ "$(status_field error)" != "None" ]; then
  ok "status carries an error message: $(status_field error | cut -c1-60)"
else bad "status has no error message"; fi
# pg_dump's error text contains double quotes; this is the case that would
# corrupt a naively-written status file.
assert_true "status.json still valid JSON after an error containing quotes" status_is_json
# The failed pass must not have destroyed the good dump that was already there.
assert_eq "existing dump survived the failed pass" "1" "$(status_field backup_count)"

# Restore a good status for the rest of the run.
run_backup_pass >/dev/null 2>&1

# ---------------------------------------------------------------------------
step "Retention pruning"
# ---------------------------------------------------------------------------
# Run against a scratch directory via BACKUP_DIR so this can age files freely
# without disturbing the real dump the restore test below depends on. No
# database is needed: when today's dump already exists the pass is prune-only.
prune_pass() {
  # prune_pass <retention_days> <setup shell snippet>
  docker run --rm -v "$PROJECT-scratch:/scratch" "$IMAGE" bash -c "
    rm -rf /scratch/pg_backups /scratch/status; mkdir -p /scratch/pg_backups; $2"
  docker run --rm \
    -e BACKUP_DIR=/scratch/pg_backups -e STATUS_DIR=/scratch/status \
    -e BACKUP_RETENTION_DAYS="$1" -e PGDATABASE="$DB_NAME" \
    -v "$PROJECT-scratch:/scratch" \
    -v "$SCRIPT_DIR:/backup-scripts:ro" \
    "$IMAGE" bash /backup-scripts/pg_backup.sh >/dev/null 2>&1
  docker run --rm -v "$PROJECT-scratch:/scratch" "$IMAGE" \
    sh -c 'ls -1 /scratch/pg_backups 2>/dev/null | sort | tr "\n" " "'
}

TODAY_FILE="$DB_NAME-$TODAY.sql.gz"
REMAINING="$(prune_pass 14 "
  touch -d '40 days ago' /scratch/pg_backups/$DB_NAME-old-40.sql.gz
  touch -d '20 days ago' /scratch/pg_backups/$DB_NAME-old-20.sql.gz
  touch -d '5 days ago'  /scratch/pg_backups/$DB_NAME-recent-5.sql.gz
  touch /scratch/pg_backups/$TODAY_FILE")"
# Listing is `ls | sort`, so the date-stamped name sorts before "recent-".
assert_eq "prunes past retention, keeps what's inside it" \
  "$TODAY_FILE $DB_NAME-recent-5.sql.gz " "$REMAINING"

# The guard that matters: if every dump on disk is older than the retention
# window, pruning must still leave the newest one. Without it, a backup that had
# been failing for longer than the window would end with pruning deleting the
# last good dump — turning one broken backup into total data loss.
REMAINING="$(prune_pass 1 "
  touch -d '40 days ago' /scratch/pg_backups/$DB_NAME-old-40.sql.gz
  touch -d '30 days ago' /scratch/pg_backups/$DB_NAME-old-30.sql.gz
  touch -d '20 days ago' /scratch/pg_backups/$TODAY_FILE")"
assert_eq "never prunes the last remaining dump, however old" "$TODAY_FILE " "$REMAINING"

docker volume rm -f "$PROJECT-scratch" >/dev/null 2>&1

# ---------------------------------------------------------------------------
step "DISASTER: copy the dump out, then destroy the database and its volume"
# ---------------------------------------------------------------------------
docker run --rm -v "$DATA_VOL:/v" -v "$WORK_DIR:/out" "$IMAGE" \
  cp "/v/pg_backups/$DUMP_NAME" "/out/$DUMP_NAME"
assert_true "dump copied to the host" test -s "$WORK_DIR/$DUMP_NAME"
echo "  rescued $(ls -lh "$WORK_DIR/$DUMP_NAME" | awk '{print $5}') to $WORK_DIR"

docker rm -f "$DB_CONTAINER" >/dev/null
docker volume rm -f "$DATA_VOL" >/dev/null
red "  database container and data volume destroyed"

# ---------------------------------------------------------------------------
step "Pin the documented initdb gotcha"
# ---------------------------------------------------------------------------
# docs/BACKUPS.md tells the reader to copy the dump OUT before restoring,
# because postgres will not initialize into a non-empty directory. Prove it,
# so the doc can't quietly become wrong.
docker volume create "$DATA_VOL-dirty" >/dev/null
docker run --rm -v "$DATA_VOL-dirty:/v" "$IMAGE" \
  sh -c 'mkdir -p /v/pg_backups && echo x > /v/pg_backups/leftover.sql.gz' >/dev/null
DIRTY_OUT="$(docker run --rm --name "$PROJECT-dirty" \
  -e POSTGRES_DB="$DB_NAME" -e POSTGRES_USER="$DB_USER" -e POSTGRES_PASSWORD="$DB_PASS" \
  -v "$DATA_VOL-dirty:/var/lib/postgresql/data" "$IMAGE" 2>&1)"
if echo "$DIRTY_OUT" | grep -qi 'not empty\|exists but is not empty'; then
  ok "postgres refuses to initialize over a non-empty data dir (as documented)"
else
  bad "expected an initdb 'not empty' failure; got: $(echo "$DIRTY_OUT" | tail -2 | tr '\n' ' ')"
fi
docker volume rm -f "$DATA_VOL-dirty" >/dev/null

# ---------------------------------------------------------------------------
step "RESTORE onto a genuinely fresh volume"
# ---------------------------------------------------------------------------
start_db "$DATA_VOL"
green "  fresh postgres up on an empty volume"

EMPTY_COUNT="$(psql_db -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")"
assert_eq "fresh database really is empty" "0" "$EMPTY_COUNT"

# This is the exact command docs/BACKUPS.md gives the reader.
RESTORE_OUT="$(gunzip -c "$WORK_DIR/$DUMP_NAME" | docker exec -i "$DB_CONTAINER" \
  psql -v ON_ERROR_STOP=1 -U "$DB_USER" -d "$DB_NAME" 2>&1)"
RESTORE_RC=$?
assert_eq "restore command exits 0" "0" "$RESTORE_RC"
if echo "$RESTORE_OUT" | grep -qi 'error'; then
  bad "restore emitted errors: $(echo "$RESTORE_OUT" | grep -i error | head -3 | tr '\n' ' ')"
else
  ok "restore emitted no errors"
fi

# ---------------------------------------------------------------------------
step "Verify the restored data is identical"
# ---------------------------------------------------------------------------
AFTER_FP="$(psql_db -tAc "$FINGERPRINT_SQL")"
echo "  fingerprint after:  $AFTER_FP"
assert_eq "content fingerprint matches (counts + md5 of every row)" "$BEFORE_FP" "$AFTER_FP"

BIG="$(psql_db -tAc "SELECT length(bio) FROM person WHERE name='Big Bio'")"
assert_eq "wide row survived intact" "540000" "$BIG"

UNI="$(psql_db -tAc "SELECT name FROM person WHERE email='zhang@example.edu'")"
assert_eq "unicode survived" "张伟" "$UNI"

QUOTED="$(psql_db -tAc "SELECT name FROM person WHERE email='pat@example.edu'")"
assert_eq "embedded quotes survived" "O'Brien, Pat" "$QUOTED"

BYTEA="$(psql_db -tAc "SELECT encode(headshot,'hex') FROM person WHERE name='Ada Lovelace'")"
assert_eq "binary column survived" "89504e47" "$BYTEA"

NULLS="$(psql_db -tAc "SELECT count(*) FROM person WHERE email IS NULL AND bio IS NULL")"
assert_eq "NULLs stayed NULL" "1" "$NULLS"

VIEWS="$(psql_db -tAc "SELECT count(*) FROM information_schema.views WHERE table_schema='public'")"
assert_eq "view was recreated" "1" "$VIEWS"

FK="$(psql_db -tAc "SELECT count(*) FROM information_schema.table_constraints WHERE constraint_type='FOREIGN KEY' AND table_schema='public'")"
assert_eq "foreign key was recreated" "1" "$FK"

# A restored serial whose sequence was not restored will collide on next insert.
# head -1: psql prints the RETURNING row and then the "INSERT 0 1" status tag.
NEWID="$(psql_db -tAc "INSERT INTO person (name) VALUES ('Post Restore') RETURNING id" | head -1)"
assert_eq "sequence restored (next insert does not collide)" "8" "$NEWID"

# ---------------------------------------------------------------------------
step "Result"
# ---------------------------------------------------------------------------
echo "  $PASS passed, $FAIL failed"
if [ "$FAIL" -gt 0 ]; then red "BACKUP/RESTORE TEST FAILED"; exit 1; fi
green "BACKUP/RESTORE TEST PASSED — the dump restores cleanly onto an empty volume"
