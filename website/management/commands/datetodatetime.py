from django.core.management.base import BaseCommand, CommandError
from website.models import News
from datetime import datetime

class Command(BaseCommand):

    help='This is a one time use command to switch from projects having a list of people to people having project roles. This will facilitate not having to nuke the database again'
    DATES = []

    def handle(self, *args, **options):
        print('====================DATETODATETIME===========================')
        for news in News.objects.all():
            print('entering')
            d = news.date
            print('retrieved')
            Command.DATES.append(d)
            print('appended')
            print(str(d))
        print(Command.DATES)