from django.contrib import admin
from website.models import Video, Publication, Talk
from django.contrib.admin import widgets
import logging

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    # The list display lets us control what is shown in the default persons table at Home > Website > Videos
    # info on displaying multiple entries comes from http://stackoverflow.com/questions/9164610/custom-columns-using-django-admin
    list_display = ('title', 'date', 'caption', 'display_projects')

    # search_fields are used for auto-complete, see:
    #   https://docs.djangoproject.com/en/3.0/ref/contrib/admin/#django.contrib.admin.ModelAdmin.autocomplete_fields
    search_fields = ['title', 'get_video_host_str', 'date']

    # default the sort order in table to descending order by date
    ordering = ('-date',)

    def display_projects(self, obj):
        return ", ".join([project.name for project in obj.projects.all()])
    
    display_projects.short_description = 'Projects'

    def get_changeform_initial_data(self, request):
        # _logger.debug("******* get_changeform_initial_data ***********")
        # _logger.debug(f"request is {request} and request.GET is {request.GET}")

        initial = super().get_changeform_initial_data(request)
        publication_id = request.GET.get('publication_id')
        talk_id = request.GET.get('talk_id')
        if publication_id:
            _logger.debug(f"publication_id is {publication_id}")
            try:
                publication = Publication.objects.get(id=publication_id)
                initial.update({
                    'title': publication.title,
                    'date': publication.date,
                })
                # For ManyToManyField, set the initial data as a list of IDs
                initial['projects'] = publication.projects.all().values_list('id', flat=True)

            except Publication.DoesNotExist:
                pass
        elif talk_id:
            _logger.debug(f"talk_id is {talk_id}")
            try:
                talk = Talk.objects.get(id=talk_id)
                initial.update({
                    'title': talk.title,
                    'date': talk.date,
                })
                # For ManyToManyField, set the initial data as a list of IDs
                initial['projects'] = talk.projects.all().values_list('id', flat=True)
            except Talk.DoesNotExist:
                pass
        return initial

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """
        Overrides the formfield_for_manytomany method of the parent ModelAdmin class to customize the widgets 
        used for ManyToMany fields in the admin interface.

        Parameters:
        db_field (Field): The database field being processed.
        request (HttpRequest): The current Django HttpRequest object capturing all details of the request.
        **kwargs: Arbitrary keyword arguments.

        Returns:
        formfield (FormField): The formfield to be used in the admin interface for the ManyToMany field. The 
        widget of the formfield is customized based on the name of the db_field.
        """
        if db_field.name == "projects":
            kwargs["widget"] = widgets.FilteredSelectMultiple("projects", is_stacked=False)

        return super(VideoAdmin, self).formfield_for_manytomany(db_field, request, **kwargs) 