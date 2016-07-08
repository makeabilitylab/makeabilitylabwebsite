.PHONY: run
.PHONY: migrate
.PHONY: shell

run:
	python manage.py runserver

migrate:
	python manage.py migrate

shell:
	python manage.py shell
