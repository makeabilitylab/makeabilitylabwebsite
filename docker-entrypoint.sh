#!/bin/bash

# Collect static files
echo "Collecting static files"
python manage.py collectstatic --noinput

# Apply database migrations
# TODO: explore doing migration in compose yml file: https://stackoverflow.com/a/44283611
echo "Running makemigrations and migrate"
python manage.py makemigrations
python manage.py migrate

echo "Running makemigrations and migrate explicitly to website (often fixes some first-time run issues)"
python manage.py makemigrations website
python manage.py migrate website


# Start server
echo "Starting server"
python manage.py runserver 0.0.0.0:8000