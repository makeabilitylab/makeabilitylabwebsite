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
echo "User:"
whoami

ls -al

# setfacl -m u:48:rwx /code
# chown -R apache /code

# Collect static files
echo "Collecting static files"
echo "****************** STEP 1: docker-entrypoint.sh ************************"
echo "1. Collecting static files"
echo "******************************************"
python manage.py collectstatic --noinput

#python manage.py datetodatetime

# Apply database migrations
# TODO: explore doing migration in compose yml file: https://stackoverflow.com/a/44283611
echo "Running makemigrations and migrate"
echo "****************** STEP 2a: docker-entrypoint.sh ************************"
echo "2a. Running makemigrations and migrate"
echo "******************************************"
python manage.py makemigrations
python manage.py migrate

echo "Running makemigrations and migrate explicitly to website (often fixes some first-time run issues)"
echo "****************** STEP 2b: docker-entrypoint.sh ************************"
echo "2b. Running makemigrations and migrate explicitly to website (often fixes some first-time run issues)"
echo "******************************************"
python manage.py makemigrations website
python manage.py migrate website

# Start server
echo "Starting server"
echo "****************** STEP 3: docker-entrypoint.sh ************************"
echo "3. Starting server"
echo "******************************************"
python manage.py runserver 0.0.0.0:8000