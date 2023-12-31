from django.contrib import admin
from website.models import Talk
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

    # Only show 25 items per page
    list_per_page = 10

    # search_fields are used for auto-complete, see:
    #   https://docs.djangoproject.com/en/3.0/ref/contrib/admin/#django.contrib.admin.ModelAdmin.autocomplete_fields
    search_fields = ['title', 'forum_name']

    autocomplete_fields = ['video']

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
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['authors'].label = 'Speakers'
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