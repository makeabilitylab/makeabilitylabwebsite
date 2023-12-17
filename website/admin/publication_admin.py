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
        ('Pub Venue information',   {'fields': ['forum_url','pub_venue_type', 'book_title', 'forum_name', 'location', 'total_papers_submitted', 'total_papers_accepted']}),
        ('Archival Info',           {'fields': ['official_url', 'extended_abstract', 'peer_reviewed', 'award' ]}),
        ('Page Info',               {'fields': ['num_pages', 'page_num_start', 'page_num_end']}),
        ('Supplementary Artifacts', {'fields': ['poster', 'video', 'talk', 'code_repo_url']}),
        ('Project Info',            {'fields': ['projects', 'project_umbrellas']}),
        ('Keyword Info',            {'fields': ['keywords']}),
    ]
    list_display = ('title', 'forum_name', 'date')

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