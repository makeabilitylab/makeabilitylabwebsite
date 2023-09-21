#!/bin/bash

# This docker-entrypoint script is based on https://stackoverflow.com/a/33993532/388117

echo "*************** docker-entrypoint.sh ***************************"
echo "Running 'docker-entrypoint.sh', which executes three things"
echo "1. Collects static files"
echo "2. Applies database migrations"
echo "3. Starts server"
echo "******************************************"

echo "Python info:"
which python
python --version

echo ""
echo "Django version:"
python3 -m django --version

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

# This is related to the permissions issues I'm having with WSL2 and Docker
# https://stackoverflow.com/q/69575151/388117
# setfacl -m u:48:rwx /code
# chown -R apache /code

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
echo "4. Running 'python manage.py delete_unused_files' to delete unused files in file system"
echo "******************************************"
python manage.py delete_unused_files

# Start server
echo "Starting server"
echo "****************** STEP 5/5: docker-entrypoint.sh ************************"
echo "5. Starting server with 'python manage.py runserver 0.0.0.0:8000'"
echo "******************************************"
python manage.py runserver 0.0.0.0:8000