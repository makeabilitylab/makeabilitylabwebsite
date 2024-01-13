from django.contrib import admin
from website.models import Position, Person, ProjectRole
from website.models.position import Title
from website.models.person import PERSON_THUMBNAIL_SIZE
from easy_thumbnails.exceptions import InvalidImageFormatError # for handling invalid images
from website.admin_list_filters import PositionRoleListFilter, PositionTitleListFilter
from image_cropping import ImageCroppingMixin

from django.db.models import Q, Case, When, Value, IntegerField
from django.utils import timezone

from django.utils.html import format_html # for formatting thumbnails
from easy_thumbnails.files import get_thumbnailer # for generating thumbnails
import os # for checking if thumbnail file exists
from website.utils import timeutils

import logging
_logger = logging.getLogger(__name__)

class PositionInline(admin.StackedInline):

    # This line specifies that the inline model is the Position model.
    # This means that the Position records will be edited inline on the Person model's admin page.
    model = Position

    # This line specifies the name of the ForeignKey field in the Position model 
    # that links to the parent model (Person). This is necessary because the Position model 
    # has multiple ForeignKey fields linking to the Person model (person, advisor, co_advisor, 
    # grad_mentor). By setting fk_name to "person", we're specifying that the inline positions 
    # are linked to the main owner of the position (the "person" field), not any of the other roles.
    fk_name = "person"

    # This line specifies the number of empty forms to display for the inline model.
    # By setting extra to 0, we're specifying that no extra empty forms will be displayed by default.
    # The user can still add new positions by clicking on the "Add another Position" link.
    extra = 0 

    fieldsets = [
        (None,                      {'fields': ['start_date', 'end_date']}),
        ('Role and Affiliations',   {'fields': ['role', 'title', 'department', 'school']}),
        ('Advisors/Mentors',        {'fields': ['advisor', 'co_advisor', 'grad_mentor']}),
    ]

    autocomplete_fields = ['advisor', 'co_advisor', 'grad_mentor']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):

        # Check if we're loading the advisor/co-advisor widget. If so
        # we need to filter to professors
        if db_field.name == "advisor" or db_field.name == "co_advisor":
           
            # Query the Position model for professor positions
            prof_positions = Position.objects.filter(title__in=Position.get_prof_titles())

            # Get the related Person instance for "Jon Froehlich"
            jon_froehlich = Person.objects.filter(
                                position__in=prof_positions, 
                                first_name="Jon", last_name="Froehlich").distinct()

            # Get today's date
            today = timezone.now().date()

            # Get the related Person instances for the professors who are still active in the lab
            professors = (Person.objects.filter(
                                Q(position__in=prof_positions), # filter to appropriate titles
                                Q(position__start_date__lte=today), # must have started
                                Q(Q(position__end_date__gte=today) | Q(position__end_date__isnull=True))) # must not have ended
                                .order_by('first_name').distinct())

            # Annotate the queryset with a custom order field that is 1 for "Jon Froehlich" and 2 for all other professors
            professors = professors.annotate(
                custom_order=Case(
                    When(first_name="Jon", last_name="Froehlich", then=Value(1)),
                    default=Value(2),
                    output_field=IntegerField(),
                )
            )

            # Order the queryset by the custom order field, then by first name
            professors = professors.order_by('custom_order', 'first_name')

            kwargs["queryset"] = professors

        elif db_field.name == "grad_mentor":
            # Define the titles we are interested in
            titles = [Title.POST_DOC, Title.PHD_STUDENT, Title.MS_STUDENT, 
                Title.RESEARCH_SCIENTIST, Title.DIRECTOR, Title.SOFTWARE_DEVELOPER, Title.DESIGNER]

            # Get today's date
            today = timezone.now().date()

            # Gets all potential mentors based on the defined titles and whether they are 
            # currently active.
            grad_mentors = (Person.objects.filter(
                        Q(position__title__in=titles), # filter to appropriate titles
                        Q(position__start_date__lte=today), # must have started
                        Q(Q(position__end_date__gte=today) | Q(position__end_date__isnull=True))) # must not have ended
                        .order_by('first_name').distinct())

            kwargs["queryset"] = grad_mentors

        return super(PositionInline, self).formfield_for_foreignkey(db_field, request, **kwargs)

class ProjectRoleInline(admin.StackedInline):
    model = ProjectRole
    extra = 0
    autocomplete_fields = ['project']


@admin.register(Person)
class PersonAdmin(ImageCroppingMixin, admin.ModelAdmin):
    fieldsets = [
        (None,                      {'fields': ['first_name', 'middle_name', 'last_name', 'image', 'cropping', 'easter_egg', 'easter_egg_crop']}),
        ('Bio',                     {'fields': ['bio', 'personal_website', 'github']}),
        ('Socials',                 {'fields': ['twitter', 'threads', 'mastodon', 'linkedin']}),
        ('For Alumni (Next Position)', {'fields': ['next_position', 'next_position_url']}),
    ]

    exclude = ('bio_datetime_modified',) # don't show this field as it's auto-calculated

    # inlines allow us to edit models on the same page as a parent model
    # see: https://docs.djangoproject.com/en/1.11/ref/contrib/admin/#inlinemodeladmin-objects
    inlines = [PositionInline, ProjectRoleInline]

    # We must define search_fields in order to use the autocomplete_fields option
    search_fields = ['first_name', 'last_name',] 
    
    # The list display lets us control what is shown in the default persons table at Home > Website > People
    # info on displaying multiple entries comes from http://stackoverflow.com/questions/9164610/custom-columns-using-django-admin
    list_display = ('get_full_name', 'get_display_thumbnail', 'get_current_title', 'get_current_role', 'is_active', 
                    'get_start_date', 'get_end_date', 'recent_projects', 'get_project_count', 'get_pub_count',
                    'get_talk_count', 'display_time_current_position', 'display_total_time_as_member')

    list_filter = (PositionRoleListFilter, PositionTitleListFilter)

    def recent_projects(self, obj):
        # Get the three most recent projects for this person based on start_date
        recent_projects = (ProjectRole.objects.filter(person=obj)
                                     .order_by('project', '-start_date')
                                     .distinct('project')[:3])
        
        # Return the project names as a comma-separated string
        return ', '.join([str(project.project) for project in recent_projects])

    recent_projects.short_description = 'Recent Projects'  # Sets column name in admin interface

    def display_time_current_position(self, obj):
        """Displays the time in the current position"""
        duration = obj.get_time_in_current_position

        if duration:
            return timeutils.humanize_duration(duration, sig_figs=2, use_abbreviated_units=True)
        else:
            return 'N/A'
    
    display_time_current_position.short_description = 'Time in Current Position'
    
    def display_total_time_as_member(self, obj):
        """Displays the total time as a member of the lab"""
        duration = obj.get_total_time_as_member
        
        if duration:
            return timeutils.humanize_duration(duration, sig_figs=2, use_abbreviated_units=True)
        else:
            return 'N/A'
    
    display_total_time_as_member.short_description = 'Total Time as Member'

    def get_display_thumbnail(self, obj):
        if obj.image and os.path.isfile(obj.image.path):
            # Use easy_thumbnails to generate a thumbnail
            thumbnailer = get_thumbnailer(obj.image)
            thumbnail_options = {'size': (PERSON_THUMBNAIL_SIZE[0], PERSON_THUMBNAIL_SIZE[1]), 'crop': True}
            
            try:
                thumbnail_url = thumbnailer.get_thumbnail(thumbnail_options).url
                return format_html('<img src="{}" height="50" style="border-radius: 50%;"/>', thumbnail_url)
            except InvalidImageFormatError as e:
                _logger.error(f"When trying to generate a thumbnail for {obj.get_full_name()}, received a invalid image format error: {e}")
            except PermissionError as e:
                _logger.error(f"When trying to generate a thumbnail for {obj.get_full_name()}, received permission error: {e}")

        return 'No Thumbnail'
    
    get_display_thumbnail.short_description = 'Thumbnail'


