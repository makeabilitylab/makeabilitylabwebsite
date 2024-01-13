import logging
from django.core.management.base import BaseCommand
from website.models import Person, ProjectRole

# Get an instance of a logger
_logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = """This command automatically closes ProjectRoles for people who have left the lab
              by setting null end_dates of ProjectRoles to the date they left the lab.
           """

    def handle(self, *args, **options):
        _logger.debug("Running auto_close_project_roles.py command to close project roles for people who have left the lab...")
       
        # Iterate over all Person instances
        list_persons_updated = []
        list_project_roles_updated = []
        for person in Person.objects.all():
            # Get the latest end_date among the person's positions
            latest_position = person.get_latest_position
            
            # If the person has a latest_position and it has an end_date and the person is no longer active
            if latest_position and latest_position.end_date is not None and person.is_active == False:
                
                # Get ProjectRoles related to the Person that have a null end_date
                project_roles_to_close = ProjectRole.objects.filter(person=person, end_date__isnull=True)

                # Log and update the ProjectRoles that will be automatically closed
                for project_role in project_roles_to_close:
                    # Use the earlier of the project's end_date and the position's end_date
                    end_date = min(project_role.project.end_date, latest_position.end_date) if project_role.project.end_date else latest_position.end_date
                    
                    _logger.info(f"Automatically closing ProjectRole: {project_role} for Person: {person} with end_date: {end_date}")
                    
                    # Update end_date of the ProjectRole
                    project_role.end_date = end_date

                    # NEED TO UNCOMMENT THIS AFTER WE TEST
                    project_role.save()

                    list_project_roles_updated.append(project_role)

                    # Track who has been updated
                    list_persons_updated.append(person)

        _logger.info(f"Updated {len(list_persons_updated)} Person instances and {len(list_project_roles_updated)} ProjectRole instances")
