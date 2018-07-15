from django.core.management.base import BaseCommand, CommandError
from website.models import News
from datetime import datetime

class Command(BaseCommand):

    help='This is a one time use command to switch from projects having a list of people to people having project roles. This will facilitate not having to nuke the database again'

    def handle(self, *args, **options):
        for news in News.objects.all():
            print("COMANNNDNDNNDNDNDNDNND")
            d = news.date.date()
            print(d)
            n_date = datetime.combine(d, datetime.min.time())
            news.date = n_date
            news.save()
            