from django.contrib import admin
from website.models import Position, Person, ProjectRole
from website.models.person import PERSON_THUMBNAIL_SIZE
from website.admin_list_filters import PositionRoleListFilter, PositionTitleListFilter
from image_cropping import ImageCroppingMixin

from django.db.models import Q
from django.utils import timezone

from django.utils.html import format_html # for formatting thumbnails
from easy_thumbnails.files import get_thumbnailer # for generating thumbnails
import os # for checking if thumbnail file exists
from website.utils import timeutils

class PositionInline(admin.StackedInline):
    model = Position

    # This specifies that the Inline is linked to the main owner of the position rather than any of the advisor roles.
    fk_name = "person"

    # This specifies that the field appears only once (by default)
    extra = 0

    def formfield_for_foreignkey(self, db_field, request, **kwargs):

        # Check if we're loading the advisor/co-advisor widget. If so
        # we need to filter to professors
        if db_field.name == "advisor" or db_field.name == "co_advisor":
           
            # Query the Position model
            prof_positions = Position.objects.filter(title__in=Position.get_prof_titles())

            # Get the related Person instances
            professors = Person.objects.filter(position__in=prof_positions).order_by('first_name').distinct()

            kwargs["queryset"] = professors

        elif db_field.name == "grad_mentor":
            # Define the titles we are interested in
            titles = [Position.POST_DOC, Position.PHD_STUDENT, Position.MS_STUDENT, 
                Position.RESEARCH_SCIENTIST, Position.SOFTWARE_DEVELOPER, Position.DESIGNER]

            # Get today's date
            today = timezone.now().date()

            # Query the database
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


@admin.register(Person)
class PersonAdmin(ImageCroppingMixin, admin.ModelAdmin):
    exclude = ('bio_datetime_modified',) # don't show this field as it's auto-calculated

    # inlines allow us to edit models on the same page as a parent model
    # see: https://docs.djangoproject.com/en/1.11/ref/contrib/admin/#inlinemodeladmin-objects
    inlines = [PositionInline, ProjectRoleInline]

    # We must define search_fields in order to use the autocomplete_fields option
    search_fields = ['first_name', 'last_name'] 

    # The list display lets us control what is shown in the default persons table at Home > Website > People
    # info on displaying multiple entries comes from http://stackoverflow.com/questions/9164610/custom-columns-using-django-admin
    list_display = ('get_full_name', 'get_display_thumbnail', 'get_current_title', 'get_current_role', 'is_active', 
                    'get_start_date', 'get_end_date', 'get_project_count', 'get_pub_count',
                    'get_talk_count', 'display_time_current_position', 'display_total_time_as_member')

    list_filter = (PositionRoleListFilter, PositionTitleListFilter)

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
            thumbnail_url = thumbnailer.get_thumbnail(thumbnail_options).url

            return format_html('<img src="{}" height="50" style="border-radius: 50%;"/>', thumbnail_url)
        return 'No Thumbnail'
    
    get_display_thumbnail.short_description = 'Thumbnail'


