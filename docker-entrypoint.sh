#!/bin/bash

# This docker-entrypoint script is based on https://stackoverflow.com/a/33993532/388117

echo "*************** docker-entrypoint.sh ***************************"
echo "Running 'docker-entrypoint.sh', which executes three things"
echo "1. Collects static files"
echo "2. Applies database migrations"
echo "3. Starts server"
echo "******************************************"

echo "But first, let's print out some environment-related contexts to ensure we're all on the same page:"
echo ""

echo "Python info:"
which python
python --version

echo ""
echo "Django version:"
python3 -m django --version

echo ""
echo "pip3 list:"
pip3 list

echo ""
echo "User (whoami output):"
whoami

echo ""
echo "pwd":
pwd

echo ""
echo "Directory (la -al) info:"
ls -al

echo ""
echo "Directory info for media (la -al media):"
ls -al media

echo ""

# This is related to the permissions issues I'm having with WSL2 and Docker
# https://stackoverflow.com/q/69575151/388117
# setfacl -m u:48:rwx /code
# chown -R apache /code

# Capture build/version info for the /version/ endpoint (#1366).
# The servers deploy via git, so .git is present and `git rev-parse` works; we
# capture the short SHA + a timestamp ONCE here (not per request) into a small
# build-info.json that website/views/version.py reads. Falls back to "unknown"
# if git isn't available (the view also tolerates a missing file).
#
# On the servers /code is a bind-mount whose .git is owned by apache:makelab
# while this script runs as root, so git's "dubious ownership" guard would
# otherwise refuse to run -- mark /code safe first (-c is process-local, no
# global config side effects). git is installed in the Dockerfile.
echo "****************** STEP -1/5: docker-entrypoint.sh ************************"
echo "-1. Writing build-info.json (git sha + build timestamp) for /version/"
echo "******************************************"
GIT_SHA=$(git -c safe.directory=/code -C /code rev-parse --short HEAD 2>/dev/null || echo "unknown")
BUILT_AT=$(date --iso-8601=seconds 2>/dev/null || echo "unknown")
printf '{"git_sha": "%s", "built_at": "%s"}\n' "$GIT_SHA" "$BUILT_AT" > build-info.json
cat build-info.json

# Collect static files
echo "****************** STEP 0/5: docker-entrypoint.sh ************************"
echo "0. Printing environment variables visible to Django"
echo "******************************************"
python manage.py print_environment_vars

# Collect static files
echo "****************** STEP 1/5: docker-entrypoint.sh ************************"
echo "1. Collecting static files"
echo "******************************************"
python manage.py collectstatic --noinput

#python manage.py datetodatetime

# Apply database migrations
# TODO: explore doing migration in compose yml file: https://stackoverflow.com/a/44283611
echo "****************** STEP 2/5: docker-entrypoint.sh ************************"
echo "2. Running makemigrations and migrate"
echo "******************************************"
python manage.py makemigrations
python manage.py migrate

echo "****************** STEP 3/5: docker-entrypoint.sh ************************"
echo "3. Running makemigrations and migrate explicitly to website (often fixes some first-time run issues)"
echo "******************************************"
python manage.py makemigrations website
python manage.py migrate website

echo "****************** STEP 4/5: docker-entrypoint.sh ************************"
echo "4.0 Running 'python manage.py delete_unused_files' to delete unused files in file system"
echo "******************************************"
python manage.py delete_unused_files

echo "****************** STEP 4.1/5: docker-entrypoint.sh ************************"
echo "4.1 Running 'python manage.py thumbnail_cleanup' to delete unused thumbnails"
echo "******************************************"
python manage.py thumbnail_cleanup

echo "****************** STEP 4.2/5: docker-entrypoint.sh ************************"
echo "4.2 Running 'python manage.py generate_slugs_for_old_news_items' to generate slugs for old news items"
echo "******************************************"
python manage.py generate_slugs_for_old_news_items

echo "****************** STEP 4.2b/5: docker-entrypoint.sh ************************"
echo "4.2b Running 'python manage.py normalize_news_image_styles' to make legacy news images responsive (#1269)"
echo "******************************************"
python manage.py normalize_news_image_styles

echo "****************** STEP 4.3/5: docker-entrypoint.sh ************************"
echo "4.3 Running 'python manage.py auto_close_project_roles' to auto-close project roles"
echo "******************************************"
python manage.py auto_close_project_roles

echo "****************** STEP 4.4/5: docker-entrypoint.sh ************************"
echo "4.4 Running 'python manage.py remove_year_from_forum_name' to remove year from forum names"
echo "******************************************"
python manage.py remove_year_from_forum_name

echo "****************** STEP 4.5/5: docker-entrypoint.sh ************************"
echo "3.1 Running 'python manage.py fix_sortedm2m_columns' to fix any missing sort_value columns"
echo "******************************************"
python manage.py fix_sortedm2m_columns

echo "****************** STEP 4.6/5: docker-entrypoint.sh ************************"
echo "4.6 Running 'python manage.py backfill_num_pages' to fill missing publication page counts"
echo "******************************************"
python manage.py backfill_num_pages

echo "****************** STEP 4.7/5: docker-entrypoint.sh ************************"
echo "4.7 Running 'python manage.py backfill_project_visibility' to resolve is_visible for legacy projects"
echo "******************************************"
python manage.py backfill_project_visibility

echo "****************** STEP 4.7b/5: docker-entrypoint.sh ************************"
echo "4.7b Running 'python manage.py backfill_original_filenames' to recover original upload filenames for never-renamed artifacts (#1391)"
echo "******************************************"
python manage.py backfill_original_filenames

echo "****************** STEP 4.8/5: docker-entrypoint.sh ************************"
echo "4.8 Running 'python manage.py recompute_url_names' to de-collide historical url_names (#1206)"
echo "******************************************"
python manage.py recompute_url_names

echo "****************** STEP 4.8b/5: docker-entrypoint.sh ************************"
echo "4.8b Running 'python manage.py seed_project_aliases' to redirect renamed project slugs (#944)"
echo "******************************************"
python manage.py seed_project_aliases

echo "****************** STEP 4.9/5: docker-entrypoint.sh ************************"
echo "4.9 Running 'python manage.py propagate_publication_projects' to link talks/videos/posters to their publication's projects (#649)"
echo "******************************************"
python manage.py propagate_publication_projects

echo "****************** STEP 4.10/5: docker-entrypoint.sh ************************"
echo "4.10 Running 'python manage.py setup_admin_groups' to create/refresh the Editors and Contributors admin groups (#1125)"
echo "******************************************"
python manage.py setup_admin_groups

echo "****************** STEP 4.10b/5: docker-entrypoint.sh ************************"
echo "4.10b Running 'python manage.py restandardize_artifact_filenames' to rename legacy talk/poster/pub files to the standardized scheme (#1401)"
echo "******************************************"
python manage.py restandardize_artifact_filenames

# echo "****************** STEP 4.3/5: docker-entrypoint.sh ************************"
# echo "4.3 Running 'python manage.py rename_person_images' to rename person images"
# echo "******************************************"
# python manage.py rename_person_images

# echo "****************** STEP 4.4/5: docker-entrypoint.sh ************************"
# echo "4.4 Running 'python manage.py rename_talk_files' to rename talk files"
# echo "******************************************"
# python manage.py rename_talk_files

# Start server
#
# Production-grade environments (TEST, PROD) run Gunicorn, the recommended WSGI
# server. Local development (DJANGO_ENV=DEBUG) keeps Django's `runserver` for
# its auto-reload on code edits, friendlier tracebacks, debug toolbar, and
# static-file serving under DEBUG=True. See issue #1034.
#
# This swap is entirely inside the container -- UW CSE's Apache still reverse-
# proxies dynamic requests to 127.0.0.1:8571 (-> container :8000) and serves
# /static/ and /media/ directly, exactly as before -- so it ships via the
# normal push-to-deploy path with no Apache/IT changes.
#
# Gunicorn tuning (overridable via env vars in the compose file):
#   GUNICORN_WORKERS  number of worker processes. The (2*cores)+1 rule of thumb
#                     would be ~49 on the 24-core host, but that box is SHARED
#                     with all Project Sidewalk instances (see #959), so we
#                     default to a modest 3.
#   GUNICORN_TIMEOUT  per-request worker timeout in seconds. Gunicorn's default
#                     of 30s can kill slow admin operations (ImageMagick/PDF
#                     thumbnail generation), so we default to 120.
echo "****************** STEP 5/5: docker-entrypoint.sh ************************"
if [ "$DJANGO_ENV" = "TEST" ] || [ "$DJANGO_ENV" = "PROD" ]; then
  GUNICORN_WORKERS="${GUNICORN_WORKERS:-3}"
  GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-120}"
  echo "5. Starting Gunicorn (DJANGO_ENV=$DJANGO_ENV, workers=$GUNICORN_WORKERS, timeout=${GUNICORN_TIMEOUT}s)"
  echo "******************************************"
  exec gunicorn makeabilitylab.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "$GUNICORN_WORKERS" \
    --timeout "$GUNICORN_TIMEOUT" \
    --access-logfile - \
    --error-logfile -
else
  echo "5. Starting dev server with 'python manage.py runserver 0.0.0.0:8000' (DJANGO_ENV=$DJANGO_ENV)"
  echo "******************************************"
  exec python manage.py runserver 0.0.0.0:8000
fi