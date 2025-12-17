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

# echo "****************** STEP 4.3/5: docker-entrypoint.sh ************************"
# echo "4.3 Running 'python manage.py rename_person_images' to rename person images"
# echo "******************************************"
# python manage.py rename_person_images

# echo "****************** STEP 4.4/5: docker-entrypoint.sh ************************"
# echo "4.4 Running 'python manage.py rename_talk_files' to rename talk files"
# echo "******************************************"
# python manage.py rename_talk_files

# Start server
echo "Starting server"
echo "****************** STEP 5/5: docker-entrypoint.sh ************************"
echo "5. Starting server with 'python manage.py runserver 0.0.0.0:8000'"
echo "******************************************"
python manage.py runserver 0.0.0.0:8000