# Makeability Lab Website
The Makeability Lab is a an HCI/Ubicomp research lab at the University of Washington directed by Professor Jon Froehlich. Founded in 2012 by Froehlich and students, the Makeability Lab focuses on designing and studying novel interactive experiences that cross between bits and atoms—the virtual and the physical—and back again to confront some of the world's greatest challenges in environmental sustainability, health and wellness, education, and universal accessibility. This repository contains the Makeability Lab's Django 1.9 (python 3.5) based site.

# Installation
The full step-by-step instructions for installation are [here](https://docs.google.com/document/d/149S_SHOzkJOhNHU4ENMU0YCbk-Vy92y5ZSTeCXG9Bhc/edit) (invite only for now).

## Requirements
* Python 3.51
* Pip 3
* Django 1.9
* ImageMagick
* ghostscript
* django_extensions (pip)
* Pillow (pip)
* Wand (pip)
* bibtex parser (pip)
* xmltodict (pip)
* django-image-cropping (pip)
* easy-thumbnails (pip)
* django-sortedm2m (pip)
* requests (pip)
* sqlite3 (for development)
* postgres (for production)
* gunicorn (for production)

Optional dependencies
* Virtual Env (for encapsulating the projects dependencies)

## Development
1. Install all dependencies. Pip dependencies can be installed using the requirements.txt file `pip install -r requirements.txt` from the project root, once the repository has been cloned.
2. Create the local database. On development we use sqlite. This can be done using `make migrate` if make is installed. Otherwise one must run `python manage.py makemigrations website && python manage.py migrate`
3. Create a super user using `python manage.py createsuperuser` to manage the admin interface.
4. The scripts `python manage.py importpubs` and `python manage.py importtalks` will import from bibtex and xml files located under the import directory respectively. These files are designed for use by the Makeability lab and will import from Jon Froehlich's website cs.umd.edu/~jonf
5. Add a file googleaccount.py in the website directory. This file should contain only the line ANALYTICS_ACCOUNT = 'your_google_analytics_email'. Replace your_google_analytics_email with whatever google account has been set up to track the domain in google analytics.
6. Follow the instructions [here](https://developers.google.com/analytics/devguides/reporting/core/v3/quickstart/service-py) to install google analytics api using pip, and to download the p12 private key from google analytics for authentication. This file should also go in the website directory along with the googleaccount.py file.
7. Run server using `make run` or `python manage.py runserver` if make is not installed.

## Production
Your production settings will vary. The makeability lab uses gunicorn and nginx to serve our site in production.



