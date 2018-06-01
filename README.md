# Makeability Lab Website
The Makeability Lab is a an HCI/Ubicomp research lab at the University of Washington directed by Professor Jon Froehlich. Founded in 2012 by Froehlich and students, the Makeability Lab focuses on designing and studying novel interactive experiences that cross between bits and atoms—the virtual and the physical—and back again to confront some of the world's greatest challenges in environmental sustainability, health and wellness, education, and universal accessibility. This repository contains the Makeability Lab's Django 1.9 (python 3.5) based site.

# Docker Installation
1. If you don't have Docker yet, you can install it here: https://docs.docker.com/install/. Open up the application. Run `docker version` to make sure that it is running.
2. Clone this repository using `git clone` and navigate to the project home directory using the `cd` command.
3. Build the docker images. You can do this by running `docker build .`. Alternatively, you can run `docker build . -t [tag]` to give your build a name. This step takes a while the first time (~2-3 min). If you don't add a tag to your build in step 3, you can look at the last line of the build that says `Successfully built [tag]` to get your tag.
4. Open the interactive bash terminal using `docker run -ti --entrypoint=bash [tag]`
5. Create the local database. Run the following commands: `python3 manage.py makemigrations website` and `python3 manage.py migrate`. Type `exit` to leave the interactive terminal.
6. Create the superuser. Run `docker run -ti -v database:/code/db -v $(pwd)/media:/code/media --entrypoint=python [tag] manage.py createsuperuser`.
7. Rebuild the docker images. Use `docker build . [-t] [tag]`
8. Run the server using Docker. `docker run -p 8000:8000 -ti -v database:/code/db -v $(pwd)/media:/code/media [tag]` 
9. Open the development server in the web browser. 

### Sample setup:
```
git clone https://github.com/jonfroehlich/makeabilitylabwebsite.git
cd makeabilitylabwebsite/
docker build . -t version1
docker run -ti --entrypoint=bash version1
python3 manage.py makemigrations website
python3 manage.py migrate
exit
docker run -ti -v database:/code/db -v $(pwd)/media:/code/media --entrypoint=python version1 manage.py createsuperuser
docker build . -t version1
docker run -p 8000:8000 -ti -v database:/code/db -v $(pwd)/media:/code/media version1
```

## Setting up Docker in PyCharm
We recommend using PyCharm as an IDE. You can configure Docker in PyCharm using the following steps:

1. Go to Run > Run 'makeabilitylabwebsite/Dockerfile'. The initial setup for this will take a minute or so. 
2. Click on the dropdown menu for images. Press create container and select `pycharm:latest`. Set the Container name to be `pycharm-container`. 
3. *(Optional: Configures the container so that it will start the server)* Click on the `...` button by Bind Ports. Click the `+` button, and select the Host Port to be `8000` and the Container Port to be `8000`.
4. Right click on `pycharm-container`. Click 'Start container' to run and 'Stop container'. (Attached consoles aren't interactive, so ctrl+c doesn't work here)
5. Go to Preferences > Project > Project Interpreter. 
6. Click on the Gear button to the right of the Project Interpreter. Select the `Add...` button.
7. Open the Docker option. The Image Name should be `pycharm:latest`. 


# Deploying to Production
The Makeability Lab website auto-deploys from GitHub to the department's Docker infrastructure using webhooks:
![webhooks_screenshot](https://github.com/jonfroehlich/makeabilitylabwebsite/blob/master/media/readme/webhooks_screenshot.png "Webhooks Screenshot") When we push code to github, the new code will auto-deploy to makeabilitylab-test. When we are ready to push changes to production, we need to do the following:
```
git tag <my version number>
git push --tags
```
This will cause that tag to deploy to production. 

## Configuring the Production Server
The production server was configured largely by UW CSE's Jason Howe. Note that settings.py reads in a config.ini file to configure a connection to the PostgreSQL database. This config.ini file is *not* in git (for obvious reasons as it contains secret keys and passwords). Thus, Jason has setup a "volume mount" for this file so that the production Docker session can read that file.

## Debugging the Production Server
Currently, both makeabilitylab-test.cs.washington.edu and makeabilitylab.cs.washington.edu are logging to `/media/debug.log`. To access this, ssh into recycle.cs.washington.edu and cd to `/cse/web/research/makelab/www`. You should see the file there.

You can also view `buildlog.text`, `httpd-access.log`, and `httpd-error.log` at https://makeabilitylab-test.cs.washington.edu/logs/ and https://makeabilitylab.cs.washington.edu/logs/.

# Makeability Lab Data
There are two types of Makeability Lab data: (i) uploaded files like PDFs, PowerPoint files, images, etc. and (ii) data that goes into the database (SQLite in local dev, PostgreSQL on production).

## Uploaded Files
All data/files uploaded to the Makeability Lab website via the admin interface (e.g., talks, publications) goes into the `/media` folder. Although typically you will not ever need to manually access this folder (except, for example, to view the `debug.log`), you can do so by ssh'ing into recycle.cs.washington.edu and cd to `/cse/web/research/makelab/www`. This files area is being mapped into the `/media` folder. 

## Access to Production Database Server
The Makeability Lab website uses PostgreSQL on production, which is running on grabthar.cs.washington.edu. In the (extremely) rare instance that you need to access Postgres directly, you must do so via recycle.cs.washington.edu.

# Manual Installation
We strongly advise running the Docker-based installation since that's what the department mandates and you get an instantly configured dev environment for free. However, if you want the *pain* :) of manually installing all of the required libs, then this is how you should do it. The full step-by-step instructions for installation are [here](https://docs.google.com/document/d/149S_SHOzkJOhNHU4ENMU0YCbk-Vy92y5ZSTeCXG9Bhc/edit) (invite only for now).

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

# Troubleshooting
## Bind for 0.0.0.0:8000 failed: port is already allocated
This means that there is already some process running at `0.0.0.0:8000`. First, make to close out of any windows that might be running a local server on your computer. If this error is still occuring, there might be a Docker container that is still running. 

To delete the container, do the following steps:
1. Run `docker ps -a`.
2. A table should be displayed. Look for the row that has `0.0.0.0:8000->8000/tcp` under the ports column. Copy the container name (under the `NAMES` column). 
3. Run `docker kill [NAME]`. (EX: `docker kill confident_tereshkova`). 

## Operational Error: Table/Column does not exist
WARNING: This method resets the database. 
1. Run `make dbshell` to enter an interactive terminal to view the current tables. In the interactive terminal, type `.tables` to display all tables that are listed in the database. (If the problem is that a column doesn't exist, type `.schema [table name]` to display the information about a specific table). If the table/column doesn't exist, continue.
2. Create a second docker container that mounts the database using `docker run -ti -v database:/database ubuntu`
3. Move the database. Type: `cd /database` then `mv db.sqlite3 db.sqlite3.backup`. Exit the interactive terminal.
4. Run `make dbshell`. Find the information for the table that is missing (either entirely or just a column) using `.schema [table name]`. Copy this information.

(You should copy something that might look something like this):
```
CREATE TABLE "website_talk_keywords" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "talk_id" integer NOT NULL REFERENCES "website_talk" ("id"), "keyword_id" integer NOT NULL REFERENCES "website_keyword" ("id"));
CREATE UNIQUE INDEX "website_talk_keywords_talk_id_fbb52519_uniq" ON "website_talk_keywords" ("talk_id", "keyword_id");
CREATE INDEX "website_talk_keywords_393ebc1b" ON "website_talk_keywords" ("talk_id");
CREATE INDEX "website_talk_keywords_5c003bba" ON "website_talk_keywords" ("keyword_id");
```
5. Move the copied database back into place using: `mv db.sqlite3.backup db.sqlite3`.
6. Recreate the database. Run `make shell`. In the interactive terminal, type `python manage.py`.
7. Rerun the website with `make run`.
