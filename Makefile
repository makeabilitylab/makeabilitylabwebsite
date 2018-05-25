.PHONY: run
.PHONY: migrate
.PHONY: shell
.PHONY: gitpull
.PHONY: source
.PHONY: collectstatic
.PHONY: makemigrations
.PHONY: build-dev
.PHONY: build-prod
IMAGE_NAME=version

build:
	docker build . -t $(IMAGE_NAME)

run: build
	docker run -p 8000:8000 -ti -v database:/code/db -v $$(pwd)/media:/code/media $(IMAGE_NAME)

shell:
	docker run -ti -v database:/code/db -v $$(pwd)/media:/code/media --entrypoint=bash $(IMAGE_NAME)

dbshell:
	docker run -ti -v database:/code/db -v $$(pwd)/media:/code/media --entrypoint=python $(IMAGE_NAME) manage.py dbshell
	

# run:
#	python manage.py runserver

gitpull:
	git pull origin master

source:
	source /srv/env/bin/activate

collectstatic:
	python manage.py collectstatic

makemigrations:
	python manage.py makemigrations

migrate: makemigrations
	python manage.py migrate

# NO SHELL FOR YUO!!!
#shell:
#	python manage.py shell

build-dev: migrate
	echo "Your project has been built in a dev environment"
	python manage.py runserver

build-prod: source gitpull collectstatic migrate
	echo "Your project has been built in the production environment"
