from django.core.management.base import BaseCommand, CommandError
from website.models import Person, Project, Project_Role
from datetime import datetime

class Command(BaseCommand):

    help='This is a one time use command to switch from projects having a list of people to people having project roles. This will facilitate not having to nuke the database again'

    def handle(self, *args, **options):
        for project in Project.objects.all():
            for person in project.people.all():
                print(person.get_full_name()+" "+project.name)
                start_date = project.start_date if project.start_date else datetime.now()
                proj_role = Project_Role(person=person, project=project, start_date=start_date)
                proj_role.save()
                
