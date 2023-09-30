from django.core.management.base import BaseCommand, CommandError
import os

class Command(BaseCommand):

    help='This command prints out all the environmental variables visible to Django. Useful for debugging.'

    def handle(self, *args, **options):
        print("Environmental variables:")

        for k, v in os.environ.items():
            print(f'\t{k}={v}')