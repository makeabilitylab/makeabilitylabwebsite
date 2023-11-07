from django.contrib import admin
from django.contrib.admin import widgets
from website.models import Publication, Poster, Video, Talk
from website.admin_list_filters import PubVenueTypeListFilter, PubVenueListFilter

from sortedm2m.fields import SortedManyToManyField
from sortedm2m_filter_horizontal_widget.forms import SortedFilteredSelectMultiple

@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    fieldsets = [
        (None,                      {'fields': ['title', 'authors', 'date']}),
        ('Files',                   {'fields': ['pdf_file']}),
        ('Pub Venue information',   {'fields': ['pub_venue_url','pub_venue_type', 'book_title', 'book_title_short', 'geo_location', 'total_papers_submitted', 'total_papers_accepted']}),
        ('Archival Info',           {'fields': ['official_url', 'extended_abstract', 'peer_reviewed', 'award' ]}),
        ('Page Info',               {'fields': ['num_pages', 'page_num_start', 'page_num_end']}),
        ('Supplementary Artifacts', {'fields': ['poster', 'video', 'talk', 'code_repo_url']}),
        ('Project Info',            {'fields': ['projects', 'project_umbrellas']}),
        ('Keyword Info',            {'fields': ['keywords']}),
    ]
    list_display = ('title', 'book_title_short', 'date')

    # default the sort order in table to descending order by date
    ordering = ('-date',)

    list_filter = (PubVenueTypeListFilter, PubVenueListFilter)

    # add in auto-complete fields for talks, see:
    #   https://docs.djangoproject.com/en/3.0/ref/contrib/admin/#django.contrib.admin.ModelAdmin.autocomplete_fields
    # this addresses: https://github.com/jonfroehlich/makeabilitylabwebsite/issues/553
    # You must also update the search_fields in the respective admins like PosterAdmin, VideoAdmin, and TalkAdmin
    # these search fields become what the auto-complete function searches for filtering
    autocomplete_fields = ['poster', 'video', 'talk']

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
        form.base_fields['title'].widget.attrs['style'] = 'min-width: {}px;'.format(text_min_width)
        form.base_fields['book_title'].widget.attrs['style'] = 'min-width: {}px;'.format(text_min_width)
        form.base_fields['book_title_short'].widget.attrs['style'] = 'min-width: {}px;'.format(500)

        select_min_width = 600
        form.base_fields['poster'].widget.attrs['style'] = 'min-width: {}px;'.format(select_min_width)
        form.base_fields['video'].widget.attrs['style'] = 'min-width: {}px;'.format(select_min_width)
        form.base_fields['talk'].widget.attrs['style'] = 'min-width: {}px;'.format(select_min_width)
        return form

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        if db_field.name == "authors":
           kwargs['widget'] = SortedFilteredSelectMultiple()
        if db_field.name == "projects":
            kwargs["widget"] = widgets.FilteredSelectMultiple("projects", is_stacked=False)
        elif db_field.name == "project_umbrellas":
            kwargs["widget"] = widgets.FilteredSelectMultiple("project umbrellas", is_stacked=False)
        elif db_field.name == "keywords":
            kwargs["widget"] = widgets.FilteredSelectMultiple("keywords", is_stacked=False)
        return super(PublicationAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)