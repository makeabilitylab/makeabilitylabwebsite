from django.core.management.base import BaseCommand, CommandError
from website.models import Person

class Command(BaseCommand):
    help = 'This is a one time use command to update the url_name field for all People in the database.'

    def handle(self, *args, **options):
        print('Updating urls...')
        for person in Person.objects.all():
            print('Name: ' + person.first_name + person.last_name)
            person.url_name = (person.first_name + person.last_name).lower()
            print('URL Name: ' + person.url_name)
            person.save()
