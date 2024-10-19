from django.contrib import admin
from website.models import Talk, Publication, PubType, TalkType
from website.admin import ArtifactAdmin
import logging

from django.utils.html import format_html # for formatting thumbnails
from easy_thumbnails.files import get_thumbnailer # for generating thumbnails
import os # for checking if thumbnail file exists

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

@admin.register(Talk)
class TalkAdmin(ArtifactAdmin):
    # The list display lets us control what is shown in the default talk table at Home > Website > Talk
    # See: https://docs.djangoproject.com/en/dev/ref/contrib/admin/#django.contrib.admin.ModelAdmin.list_display
    list_display = ('title', 'get_display_thumbnail', 'get_speakers_as_csv', 'date', 'forum_name', 'location', 'talk_type')

    # Only show N items per page
    list_per_page = 10

    # search_fields are used for auto-complete, see:
    #   https://docs.djangoproject.com/en/3.0/ref/contrib/admin/#django.contrib.admin.ModelAdmin.autocomplete_fields
    search_fields = ['title', 'forum_name']

    # TODO JEF: This auto-complete field is not working
    # See: https://github.com/makeabilitylab/makeabilitylabwebsite/issues/1093#issuecomment-2423843958
    # autocomplete_fields = ['video']

    # fieldsets control how the "add/change" admin views look
    # Specifically, it controls the hierarchical layout of the admin form
    fieldsets = [
        (None,                      {'fields': ['title', 'authors', 'date']}),
        ('Files',                   {'fields': ['pdf_file', 'raw_file']}),
        ('Talk Venue Info',         {'fields': ['talk_type', 'forum_name', 'forum_url', 'location']}),
        ('Links',                   {'fields': ['video', 'slideshare_url']}),
        ('Project Info',            {'fields': ['projects', 'project_umbrellas']}),
        ('Keyword Info',            {'fields': ['keywords']}),
    ]

    ordering = ('-date',)  # Sort talks by date in descending order
    list_filter = ('talk_type',)  # Add a filter for the talk type

    def get_changeform_initial_data(self, request):
        # _logger.debug("******* get_changeform_initial_data ***********")
        # _logger.debug(f"request is {request} and request.GET is {request.GET}")

        initial = super().get_changeform_initial_data(request)
        publication_id = request.GET.get('publication_id')
        if publication_id:
            _logger.debug(f"publication_id is {publication_id}")
            try:
                publication = Publication.objects.get(id=publication_id)
                initial.update({
                    'title': publication.title,
                    'date': publication.date,
                    'forum_name': publication.forum_name,
                    'forum_url': publication.forum_url,
                    'location': publication.location,

                })
                # For ManyToManyField, set the initial data as a list of IDs
                initial['authors'] = publication.authors.all().values_list('id', flat=True)
                initial['projects'] = publication.projects.all().values_list('id', flat=True)
                initial['project_umbrellas'] = publication.project_umbrellas.all().values_list('id', flat=True)
                initial['keywords'] = publication.keywords.all().values_list('id', flat=True)
            
                if publication.pub_venue_type == PubType.CONFERENCE:
                    initial['talk_type'] = TalkType.CONFERENCE_TALK

            except Publication.DoesNotExist:
                pass
        return initial

    def get_form(self, request, obj=None, **kwargs):
        """
        Overrides the get_form method of the parent ModelAdmin class to customize the form used in the admin interface.

        Parameters:
        request (HttpRequest): The current Django HttpRequest object capturing all details of the request.
        obj (Model, optional): The database object being edited. Default is None, which means this is a new object.
        **kwargs: Arbitrary keyword arguments.

        Returns:
        form (ModelForm): The form to be used in the admin interface. The 'authors' field label is changed to 'Speakers'.
        """
        # _logger.debug("******* get_form ***********")
        # _logger.debug(f"request is {request} and obj is {obj} and kwargs is {kwargs}")
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['authors'].label = 'Speakers'

        text_min_width = 750
        form.base_fields['title'].widget.attrs['style'] = f'min-width: {text_min_width}px;'
        form.base_fields['forum_name'].widget.attrs['style'] = f'min-width: 500px;'

        return form
    
    def get_display_thumbnail(self, obj):
        if obj.thumbnail and os.path.isfile(obj.thumbnail.path):
            # Use easy_thumbnails to generate a thumbnail
            thumbnailer = get_thumbnailer(obj.thumbnail)
            thumbnail_options = {'size': (100, 56), 'crop': True}
            thumbnail_url = thumbnailer.get_thumbnail(thumbnail_options).url

            return format_html('<img src="{}" width="100" />', thumbnail_url)
        return 'No Thumbnail'
    
    get_display_thumbnail.short_description = 'Thumbnail'

    def change_view(self, request, object_id, form_url='', extra_context=None):
        _logger.debug("******* change_view ********")
        _logger.debug(f"request is {request} request.GET is {request.GET}")

        # Add the talk_id to the context so that we can use it in the template
        extra_context = extra_context or {}
        extra_context['talk_id'] = object_id
        return super().change_view(request, object_id, form_url, extra_context)
    