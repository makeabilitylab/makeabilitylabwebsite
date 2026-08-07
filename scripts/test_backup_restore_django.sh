#!/bin/bash
#
# Second half of the #1443 backup proof: does a dump of the REAL Makeability
# Lab schema restore into a database Django will still run against?
#
# scripts/test_backup_restore.sh proves the dump mechanics (encoding, binary
# columns, sequences, constraints) on a synthetic schema. This one proves the
# thing that actually matters in a disaster: after restoring, Django considers
# the database complete and current — `migrate --check` passes, `check` passes,
# and the content is all still there.
#
# Namespaced under mldjtest-* and torn down at the end. It never touches the
# developer's own stack, database, or volumes — but note it DOES write
# website/migrations/ in this working tree, exactly as a normal container start
# does (that directory is gitignored and per-environment by design).
#
# Usage:
#   bash scripts/test_backup_restore_django.sh
#
# Requires: docker, and a built website image (makeabilitylabwebsite-website).

set -uo pipefail

PROJECT=mldjtest
PG_IMAGE="${POSTGRES_IMAGE:-postgres:16}"
WEB_IMAGE="${WEBSITE_IMAGE:-makeabilitylabwebsite-website:latest}"
NET="$PROJECT-net"
DATA_VOL="$PROJECT-data"
STATUS_VOL="$PROJECT-status"
DB_CONTAINER="$PROJECT-db"
DB_NAME=makeability
DB_USER=admin
DB_PASS=password

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIR="$(mktemp -d /tmp/mldjtest.XXXXXX)"

PASS=0; FAIL=0
green() { printf '\033[32m%s\033[0m\n' "$1"; }
red()   { printf '\033[31m%s\033[0m\n' "$1"; }
step()  { printf '\n\033[1m== %s\033[0m\n' "$1"; }
ok()    { PASS=$((PASS+1)); green "  PASS  $1"; }
bad()   { FAIL=$((FAIL+1)); red   "  FAIL  $1"; }
assert_eq() { if [ "$2" = "$3" ]; then ok "$1"; else bad "$1 (expected '$2', got '$3')"; fi; }

cleanup_docker() {
  docker rm -f "$DB_CONTAINER" >/dev/null 2>&1
  docker volume rm -f "$DATA_VOL" "$STATUS_VOL" >/dev/null 2>&1
  docker network rm "$NET" >/dev/null 2>&1
}
cleanup() { cleanup_docker; rm -rf "$WORK_DIR"; }
trap cleanup EXIT

psql_db() { docker exec -i "$DB_CONTAINER" psql -v ON_ERROR_STOP=1 -U "$DB_USER" -d "$DB_NAME" "$@"; }

start_db() {
  docker run -d --name "$DB_CONTAINER" --network "$NET" --network-alias db \
    -e POSTGRES_DB="$DB_NAME" -e POSTGRES_USER="$DB_USER" -e POSTGRES_PASSWORD="$DB_PASS" \
    -v "$1:/var/lib/postgresql/data" "$PG_IMAGE" >/dev/null
  for _ in $(seq 1 60); do
    psql_db -c 'SELECT 1' >/dev/null 2>&1 && return 0
    sleep 1
  done
  red "postgres did not become ready"; exit 1
}

# Run a Django management command against the throwaway database. Root, because
# makemigrations writes into the bind-mounted working tree.
manage() {
  docker run --rm --network "$NET" --user root \
    -v "$REPO_DIR:/code" -w /code "$WEB_IMAGE" python manage.py "$@"
}

run_backup_pass() {
  docker run --rm --network "$NET" \
    -e PGHOST=db -e PGUSER="$DB_USER" -e PGPASSWORD="$DB_PASS" -e PGDATABASE="$DB_NAME" \
    -v "$DATA_VOL:/var/lib/postgresql/data" \
    -v "$STATUS_VOL:/var/backup-status" \
    -v "$REPO_DIR/scripts:/backup-scripts:ro" \
    "$PG_IMAGE" bash /backup-scripts/pg_backup.sh
}

# ---------------------------------------------------------------------------
step "Build the real Makeability Lab schema"
# ---------------------------------------------------------------------------
cleanup_docker
docker network create "$NET" >/dev/null
start_db "$DATA_VOL"
green "  postgres up"

# Same sequence docker-entrypoint.sh runs: migrations are gitignored and
# per-environment, so they are generated before being applied.
manage makemigrations website >/dev/null 2>&1
MIGRATE_OUT="$(manage migrate 2>&1)"
if [ $? -eq 0 ]; then ok "migrate built the schema"
else bad "migrate failed: $(echo "$MIGRATE_OUT" | tail -3 | tr '\n' ' ')"; fi

TABLE_COUNT="$(psql_db -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'" | tr -d ' ')"
if [ "$TABLE_COUNT" -gt 30 ]; then ok "real schema present ($TABLE_COUNT tables)"
else bad "expected a large schema, got $TABLE_COUNT tables"; fi

# ---------------------------------------------------------------------------
step "Seed content through Django's own ORM"
# ---------------------------------------------------------------------------
# Going through the ORM rather than raw SQL means the rows exercise the real
# field types: sortedm2m through-tables, image_cropping CharFields, rich text.
cat > "$WORK_DIR/seed.py" <<'PY'
from django.contrib.auth.models import User
from website.models import Person, Publication, Project, News
import datetime

u = User.objects.create_superuser('backuptest', 'backuptest@example.edu', 'x')

p1 = Person.objects.create(first_name='José', last_name='Ñuñez',
                           email='jose@example.edu', bio="Accents: é ü ñ — em dash")
p2 = Person.objects.create(first_name='张', last_name='伟', email='zhang@example.edu')
p3 = Person.objects.create(first_name="Pat", last_name="O'Brien", email='pat@example.edu')

proj = Project.objects.create(name='Sidewalk "Quoted" Project', short_name='backup-test-proj',
                              start_date=datetime.date(2020, 1, 1))

pub = Publication.objects.create(title='Notes on the Analytical Engine',
                                 date=datetime.date(2024, 5, 1))
pub.authors.add(p1, p2)          # SortedManyToManyField through-table
pub.projects.add(proj)

News.objects.create(title='Lab news with <b>HTML</b> & entities',
                    date=datetime.date(2024, 6, 1),
                    content='<p>Rich text with “curly quotes” and a — dash.</p>',
                    author=p1)

print('SEEDED')
PY
SEED_OUT="$(docker run --rm --network "$NET" --user root -v "$REPO_DIR:/code" \
  -v "$WORK_DIR/seed.py:/seed.py:ro" -w /code "$WEB_IMAGE" \
  python manage.py shell -c "exec(open('/seed.py').read())" 2>&1)"
if echo "$SEED_OUT" | grep -q SEEDED; then ok "seeded via the ORM"
else bad "seed failed: $(echo "$SEED_OUT" | tail -5 | tr '\n' ' ')"; fi

fingerprint() {
  psql_db -tAc "SELECT (SELECT count(*) FROM website_person) || '/' ||
                       (SELECT count(*) FROM website_publication) || '/' ||
                       (SELECT count(*) FROM website_project) || '/' ||
                       (SELECT count(*) FROM website_news) || '/' ||
                       (SELECT count(*) FROM website_publication_authors) || '/' ||
                       (SELECT count(*) FROM django_migrations) || '/' ||
                       (SELECT md5(string_agg(p::text, '|' ORDER BY p.id)) FROM website_person p)"
}
BEFORE_FP="$(fingerprint)"
green "  fingerprint before: $BEFORE_FP"

# ---------------------------------------------------------------------------
step "Back up, then destroy everything"
# ---------------------------------------------------------------------------
run_backup_pass | sed 's/^/  /'
assert_eq "backup pass exits 0" "0" "$?"

TODAY="$(date -u +%F)"
DUMP_NAME="$DB_NAME-$TODAY.sql.gz"
docker run --rm -v "$DATA_VOL:/v" -v "$WORK_DIR:/out" "$PG_IMAGE" \
  cp "/v/pg_backups/$DUMP_NAME" "/out/$DUMP_NAME" 2>/dev/null
if [ -s "$WORK_DIR/$DUMP_NAME" ]; then
  ok "dump rescued to the host ($(ls -lh "$WORK_DIR/$DUMP_NAME" | awk '{print $5}'))"
else bad "dump was not produced"; fi

docker rm -f "$DB_CONTAINER" >/dev/null
docker volume rm -f "$DATA_VOL" >/dev/null
red "  database container and data volume destroyed"

# ---------------------------------------------------------------------------
step "Restore onto a fresh volume"
# ---------------------------------------------------------------------------
start_db "$DATA_VOL"
RESTORE_OUT="$(gunzip -c "$WORK_DIR/$DUMP_NAME" | docker exec -i "$DB_CONTAINER" \
  psql -v ON_ERROR_STOP=1 -U "$DB_USER" -d "$DB_NAME" 2>&1)"
assert_eq "restore exits 0" "0" "$?"
if echo "$RESTORE_OUT" | grep -qi '^ERROR'; then
  bad "restore emitted errors: $(echo "$RESTORE_OUT" | grep -i '^ERROR' | head -3 | tr '\n' ' ')"
else ok "restore emitted no errors"; fi

# ---------------------------------------------------------------------------
step "Django must accept the restored database"
# ---------------------------------------------------------------------------
assert_eq "content fingerprint matches" "$BEFORE_FP" "$(fingerprint)"

# The real test of a restored Django DB: django_migrations came back intact, so
# Django sees a fully-migrated database rather than trying to re-run migrations
# over existing tables.
CHECK_OUT="$(manage migrate --check 2>&1)"
assert_eq "migrate --check reports nothing pending" "0" "$?"

SYSCHECK_OUT="$(manage check 2>&1)"
assert_eq "manage.py check passes" "0" "$?"

# Read content back through the ORM, not SQL — proves the app layer works.
cat > "$WORK_DIR/verify.py" <<'PY'
from website.models import Person, Publication, News
pub = Publication.objects.get(title='Notes on the Analytical Engine')
authors = list(pub.authors.all().values_list('email', flat=True))
news = News.objects.get(title__startswith='Lab news')
print('AUTHORS=' + ','.join(sorted(a or '' for a in authors)))
print('UNICODE=' + Person.objects.get(email='zhang@example.edu').first_name)
print('APOSTROPHE=' + Person.objects.get(email='pat@example.edu').last_name)
print('PROJECTS=' + str(pub.projects.count()))
print('CURLY=' + ('yes' if '“' in news.content else 'no'))
PY
VERIFY_OUT="$(docker run --rm --network "$NET" --user root -v "$REPO_DIR:/code" \
  -v "$WORK_DIR/verify.py:/verify.py:ro" -w /code "$WEB_IMAGE" \
  python manage.py shell -c "exec(open('/verify.py').read())" 2>&1)"
get() { echo "$VERIFY_OUT" | grep "^$1=" | head -1 | cut -d= -f2-; }

assert_eq "m2m authors restored in order"  "jose@example.edu,zhang@example.edu" "$(get AUTHORS)"
assert_eq "unicode field via ORM"          "张"    "$(get UNICODE)"
assert_eq "apostrophe field via ORM"       "O'Brien" "$(get APOSTROPHE)"
assert_eq "publication↔project m2m"        "1"     "$(get PROJECTS)"
assert_eq "rich-text curly quotes survived" "yes"  "$(get CURLY)"

# ---------------------------------------------------------------------------
step "Result"
# ---------------------------------------------------------------------------
echo "  $PASS passed, $FAIL failed"
if [ "$FAIL" -gt 0 ]; then red "DJANGO BACKUP/RESTORE TEST FAILED"; exit 1; fi
green "DJANGO BACKUP/RESTORE TEST PASSED — Django runs against the restored database"
