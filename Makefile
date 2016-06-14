.PHONY: run
.PHONY: migrate

run:
	python manage.py runserver

migrate:
	python manage.py migrate
