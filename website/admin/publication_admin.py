from django.contrib import admin
from django.contrib.admin import widgets
from website.models import Publication, Poster, Video, Talk
from website.admin_list_filters import PubVenueTypeListFilter, PubVenueListFilter
import logging

from django.utils.html import format_html # for formatting thumbnails
from easy_thumbnails.files import get_thumbnailer # for generating thumbnails
import os # for checking if thumbnail file exists

from sortedm2m.fields import SortedManyToManyField
from sortedm2m_filter_horizontal_widget.forms import SortedFilteredSelectMultiple
from website.admin import ArtifactAdmin

from django.urls import reverse
from django.utils.html import format_html

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

@admin.register(Publication)
class PublicationAdmin(ArtifactAdmin):

    # We add in some real-time js code to check some data entry
    class Media:
        js = ('website/js/pub_admin_custom.js',)

    # This organizes the fields in the admin interface into a series of subheaders ("fieldsets")
    fieldsets = [
        (None,                      {'fields': ['title', 'authors', 'date']}),
        ('Files',                   {'fields': ['pdf_file']}),
        ('Pub Venue information',   {'fields': ['forum_url','pub_venue_type', 'book_title', 'forum_name', 'location', 'total_papers_submitted', 'total_papers_accepted']}),
        ('Archival Info',           {'fields': ['official_url', 'extended_abstract', 'peer_reviewed', 'award' ]}),
        ('Page Info',               {'fields': ['num_pages', 'page_num_start', 'page_num_end']}),
        ('Supplementary Artifacts', {'fields': ['poster', 'video', 'talk', 'code_repo_url']}),
        ('Project Info',            {'fields': ['projects', 'project_umbrellas']}),
        ('Keyword Info',            {'fields': ['keywords']}),
    ]

    list_display = ('title', 'get_display_thumbnail', 'display_authors', 'forum_name', 'date', 'display_projects')

    # Only show N items per page
    list_per_page = 20

    # default the sort order in table to descending order by date
    ordering = ('-date',)

    list_filter = (PubVenueTypeListFilter, PubVenueListFilter)

    # add in auto-complete fields 
    #   this addresses: https://github.com/jonfroehlich/makeabilitylabwebsite/issues/553
    #
    # autocomplete_fields is a list of ForeignKey and/or ManyToManyField fields you would like 
    # to change to Select2 autocomplete inputs. By default, the admin uses a select-box interface (<select>) for those fields.
    # The Select2 input looks similar to the default input but comes with a search feature that loads the options asynchronously. 
    # This is faster and more user-friendly if the related model has many instances.
    #
    # You must also update the search_fields in the respective admins like PosterAdmin, VideoAdmin, and TalkAdmin
    # these search fields become what the auto-complete function searches for filtering
    # See : https://docs.djangoproject.com/en/4.2/ref/contrib/admin/#django.contrib.admin.ModelAdmin.autocomplete_fields
    # Update Nov 10, 2023: This is now broken due to weirdness with Select2 fields in the admin interface
    # See: https://github.com/makeabilitylab/makeabilitylabwebsite/issues/1093
    #autocomplete_fields = ['poster', 'video', 'talk']

    def display_projects(self, obj):
        return ", ".join([project.name for project in obj.projects.all()])
    display_projects.short_description = 'Projects'

    def display_authors(self, obj):
        authors = [author.get_full_name() for author in obj.authors.all()[:5]]
        if obj.authors.count() > 5:
            authors.append("...")
        return ", ".join(authors) if authors else 'No authors'
    display_authors.short_description = 'Authors (First 5)'

    def get_display_thumbnail(self, obj):
        if obj.thumbnail and os.path.isfile(obj.thumbnail.path):
            # Use easy_thumbnails to generate a thumbnail
            thumbnailer = get_thumbnailer(obj.thumbnail)
            thumbnail_options = {'size': (110, 142), 'crop': True}
            thumbnail_url = thumbnailer.get_thumbnail(thumbnail_options).url

            return format_html('<img src="{}" width="100" />', thumbnail_url)
        return 'No Thumbnail'
    
    get_display_thumbnail.short_description = 'Thumbnail'

    def get_form(self, request, obj=None, **kwargs):
        """We custom style some of the admin UI, including expanding the width of the talk select interface"""
        form = super(PublicationAdmin, self).get_form(request, obj, **kwargs)

        # we style the talks widget so that it's wider, see:
        #   https://docs.djangoproject.com/en/2.2/ref/forms/widgets/#customizing-widget-instances
        # see also:
        #   https://stackoverflow.com/questions/10588275/django-change-field-size-of-modelmultiplechoicefield
        #   https://stackoverflow.com/questions/110378/change-the-width-of-form-elements-created-with-modelform-in-django
        # and finally, this is what worked for me:
        #   https://stackoverflow.com/q/35211809
        # to address: https://github.com/jonfroehlich/makeabilitylabwebsite/issues/851
        text_min_width = 750
        form.base_fields['title'].widget.attrs['style'] = f'min-width: {text_min_width}px;'
        form.base_fields['book_title'].widget.attrs['style'] = f'min-width: {text_min_width}px;'
        form.base_fields['forum_name'].widget.attrs['style'] = f'min-width: 500px;'

        select_min_width = 600
        select_max_width = 800
        custom_style = f'min-width: {select_min_width}px; max-width: {select_max_width}px;'
        form.base_fields['poster'].widget.attrs['style'] = custom_style
        form.base_fields['video'].widget.attrs['style'] = custom_style
        form.base_fields['talk'].widget.attrs['style'] = custom_style
        return form
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):

        # In this code, we’re checking if the db_field is one of ‘video’, ‘talk’, or ‘poster’. 
        # If it is, we’re ordering the queryset for that field by ‘date’ in descending order (hence the ‘-date’). 
        if db_field.name in ['video', 'talk', 'poster']:
            kwargs["queryset"] = db_field.related_model.objects.order_by('-date')

        # If the db_field is not one of those fields, we’re just calling the parent class’s formfield_for_foreignkey method.
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def response_add(self, request, obj, post_url_continue=None):
        _logger.debug("******* RESPONSE ADD ********")
        _logger.debug(f"request is {request} request.GET is {request.GET}")
        if "_popup" in request.GET:
            _logger.debug("_popup exists in request.GET for response_add")
            #return HttpResponseRedirect(f'/admin/website/talk/add/?_popup=1&publication_id={obj.id}')
        return super().response_add(request, obj, post_url_continue)

    def response_change(self, request, obj):
        _logger.debug("******* RESPONSE CHANGE ********")
        _logger.debug(f"request is {request} request.GET is {request.GET}")
        if "_popup" in request.GET:
             _logger.debug("_popup exists in request.GET for response_change")
           
            #return HttpResponseRedirect(f'/admin/website/talk/add/?_popup=1&publication_id={obj.id}')
        return super().response_change(request, obj)
    
    def add_view(self, request, form_url='', extra_context=None):
        _logger.debug("******* add_view ********")
        _logger.debug(f"request is {request} request.GET is {request.GET}")
        response = super().add_view(request, form_url, extra_context)
        if "_popup" in request.GET:
            publication_id = request.GET.get('publication_id')
            # if publication_id:
                # return HttpResponseRedirect(f'/admin/website/talk/add/?_popup=1&publication_id={publication_id}')
        return response

    def change_view(self, request, object_id, form_url='', extra_context=None):
        _logger.debug("******* change_view ********")
        _logger.debug(f"request is {request} request.GET is {request.GET}")

        extra_context = extra_context or {}
        extra_context['publication_id'] = object_id
        return super().change_view(request, object_id, form_url, extra_context)
    
        # response = super().change_view(request, object_id, form_url, extra_context)
        # if "_popup" in request.GET:
        #     publication_id = object_id
        #     # return HttpResponseRedirect(f'/admin/website/talk/add/?_popup=1&publication_id={publication_id}')
        # return response

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        _logger.debug("******* formfield_for_foreignkey ********")
        _logger.debug(f"db_field is {db_field} request is {request} request.GET is {request.GET}")
        formfield = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == "talk":
            _logger.debug("db_field is talk")
            publication_id = request.resolver_match.kwargs.get('object_id')
            if publication_id:
                _logger.debug(f"publication_id is {publication_id}")
                related_url = reverse('admin:website_talk_add')
                related_url += f'?_popup=1&publication_id={publication_id}'
                formfield.widget.attrs['data-popup'] = 'yes'
                formfield.widget.attrs['href'] = related_url
        return formfield