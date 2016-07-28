.PHONY: run
.PHONY: migrate
.PHONY: shell
.PHONY: gitpull
.PHONY: source
.PHONY: collectstatic
.PHONY: makemigrations
.PHONY: build-dev
.PHONY: build-prod

run:
	python manage.py runserver

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

shell:
	python manage.py shell

build-dev: migrate
	echo "Your project has been built in a dev environment"
	python manage.py runserver

build-prod: source gitpull collectstatic migrate
	echo "Your project has been built in the production environment"
