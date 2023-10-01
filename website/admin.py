from django.contrib import admin
from django.contrib.admin import widgets
from .models import Person, Publication, Position, Talk, Project, Poster, Keyword, News, Banner, Video, ProjectHeader, Photo, ProjectUmbrella, ProjectRole, Sponsor
from website.admin_list_filters import PositionRoleListFilter, PositionTitleListFilter, PubVenueTypeListFilter, PubVenueListFilter
# from sortedm2m_filter_horizontal_widget.forms import SortedFilteredSelectMultiple
import django
from django import forms

# so we can print debug
from django.conf import settings

from django.http import HttpResponse
from datetime import datetime
from django.template import loader
from django.template import RequestContext
from django.shortcuts import redirect
from django import forms
import urllib
import bibtexparser

from image_cropping import ImageCroppingMixin

class BannerAdmin(ImageCroppingMixin, admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ["page", "title", "caption", "alt_text", "link", "favorite", "project"]}),
        # ('Image', {'fields': ["image", "image_preview"]})
        ('Image', {'fields': ["image", "cropping"]})
    ]

    # The list display lets us control what is shown in the default persons table at Home > Website > Banners
    # info on displaying multiple entries comes from http://stackoverflow.com/questions/9164610/custom-columns-using-django-admin
    list_display = ('title', 'project', 'page', 'favorite', 'image')
    # readonly_fields = ["image_preview"]


class PositionInline(admin.StackedInline):
    model = Position

    # This specifies that the Inline is linked to the main owner of the position rather than any of the advisor roles.
    fk_name = "person"

    # This specifies that the field appears only once (by default)
    extra = 0

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        print(f"PositionInline.formfield_for_foreignkey: db_field: {db_field} db_field.name {db_field.name} request: {request}")

        if db_field.name == "advisor" or db_field.name == "co_advisor":
            # Filters advisors to professors and sorts by first name
            # Based on: http://stackoverflow.com/a/30627555
            professor_ids = [person.id for person in Person.objects.all() if person.is_professor]
            filtered_persons = Person.objects.filter(id__in=professor_ids).order_by('first_name')
            print(filtered_persons)
            kwargs["queryset"] = filtered_persons
        elif db_field.name == "grad_mentor":
            # Filters grad mentor list to current grad students (either member or collaborator)
            grad_ids = [person.id for person in Person.objects.all() if person.is_grad_student \
                        and (person.is_current_member or person.is_current_collaborator)]
            
            filtered_persons = Person.objects.filter(id__in=grad_ids).order_by('first_name')
            print(filtered_persons)
            kwargs["queryset"] = filtered_persons

        return super(PositionInline, self).formfield_for_foreignkey(db_field, request, **kwargs)
    
class ProjectRoleInline(admin.StackedInline):
    model = ProjectRole
    extra = 0

class ProjectHeaderInline(ImageCroppingMixin, admin.StackedInline):
    model = ProjectHeader
    extra = 0

# Uses format as per https://github.com/jonasundderwolf/django-image-cropping to add cropping to the admin page
class NewsAdmin(ImageCroppingMixin, admin.ModelAdmin):
    # Filters authors only to current members and sorts by firstname
    # Based on: http://stackoverflow.com/a/30627555
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # print("NewsAdmin.formfield_for_foreignkey: db_field: {} db_field.name {} request: {}".format(db_field, db_field.name, request))
        if db_field.name == "author":
            current_member_ids = [person.id for person in Person.objects.all() if person.is_current_member]
            filtered_persons = Person.objects.filter(id__in=current_member_ids).order_by('first_name')
            print(filtered_persons)
            kwargs["queryset"] = filtered_persons
        return super(NewsAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        if db_field.name == "project":
            kwargs["widget"] = widgets.FilteredSelectMultiple("project", is_stacked=False)
        return super(NewsAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)


class PhotoAdmin(ImageCroppingMixin, admin.ModelAdmin):
    list_display = ('__str__', 'admin_thumbnail')

class ProjectAdmin(ImageCroppingMixin, admin.ModelAdmin):
    inlines = [ProjectHeaderInline]

    # The list display lets us control what is shown in the Project table at Home > Website > Project
    # info on displaying multiple entries comes from http://stackoverflow.com/questions/9164610/custom-columns-using-django-admin
    list_display = ('name', 'start_date', 'end_date', 'has_ended', 'get_people_count',
                    'get_current_member_count', 'get_past_member_count',
                    'get_most_recent_artifact_date', 'get_most_recent_artifact_type',
                    'get_publication_count', 'get_video_count', 'get_talk_count')

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        if db_field.name == "sponsors":
            kwargs["widget"] = widgets.FilteredSelectMultiple("sponsors", is_stacked=False)
        if db_field.name == "keywords":
            kwargs["widget"] = widgets.FilteredSelectMultiple("keywords", is_stacked=False)
        if db_field.name == "project_umbrellas":
            kwargs["widget"] = widgets.FilteredSelectMultiple("project umbrellas", is_stacked=False)
        return super(ProjectAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)

class PersonAdmin(ImageCroppingMixin, admin.ModelAdmin):

    # inlines allow us to edit models on the same page as a parent model
    # see: https://docs.djangoproject.com/en/1.11/ref/contrib/admin/#inlinemodeladmin-objects
    inlines = [PositionInline, ProjectRoleInline]

    # The list display lets us control what is shown in the default persons table at Home > Website > People
    # info on displaying multiple entries comes from http://stackoverflow.com/questions/9164610/custom-columns-using-django-admin
    list_display = ('get_full_name', 'get_current_title', 'get_current_role', 'is_active', 'get_start_date', 'get_end_date', 'get_time_in_current_position', 'get_total_time_as_member')

    #TODO setup filter here that has diff categories (like active members, past, etc.):
    #https://www.elements.nl/2015/03/16/getting-the-most-out-of-django-admin-filters/
    #related to: https://github.com/jonfroehlich/makeabilitylabwebsite/issues/238
    list_filter = (PositionRoleListFilter, PositionTitleListFilter)

class VideoAdmin(admin.ModelAdmin):
    # The list display lets us control what is shown in the default persons table at Home > Website > Videos
    # info on displaying multiple entries comes from http://stackoverflow.com/questions/9164610/custom-columns-using-django-admin
    list_display = ('title', 'date', 'caption', 'project')

    # search_fields are used for auto-complete, see:
    #   https://docs.djangoproject.com/en/3.0/ref/contrib/admin/#django.contrib.admin.ModelAdmin.autocomplete_fields
    search_fields = ['title', 'get_video_host_str', 'date']

    # default the sort order in table to descending order by date
    ordering = ('-date',)

class TalkAdmin(admin.ModelAdmin):
    # The list display lets us control what is shown in the default talk table at Home > Website > Talk
    # See: https://docs.djangoproject.com/en/dev/ref/contrib/admin/#django.contrib.admin.ModelAdmin.list_display
    list_display = ('title', 'date', 'get_speakers_as_csv', 'forum_name', 'location', 'talk_type')

    # search_fields are used for auto-complete, see:
    #   https://docs.djangoproject.com/en/3.0/ref/contrib/admin/#django.contrib.admin.ModelAdmin.autocomplete_fields
    # for example, the PublicationAdmin uses auto-complete select2 for talks
    search_fields = ['title', 'forum_name']

    # Filters speakers only to current members and collaborators and sorts by first name
    # Based on: https://stackoverflow.com/a/17457828
    # Update: we no longer do this because sometimes we want to add a talk by a former member or collaborator
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        print("TalkAdmin.formfield_for_manytomany: db_field: {} db_field.name {} request: {}".format(db_field, db_field.name, request))
        if db_field.name == "projects":
            kwargs["widget"] = widgets.FilteredSelectMultiple("projects", is_stacked=False)
        if db_field.name == "project_umbrellas":
            kwargs["widget"] = widgets.FilteredSelectMultiple("project umbrellas", is_stacked=False, )
        if db_field.name == "speakers":
            # Uncomment the following block of code to limit the speakers field in the admin UI only to current lab members
            # Note: we don't actually want to do this (see https://github.com/jonfroehlich/makeabilitylabwebsite/issues/534)
            # but keeping it here because code may be useful in the future for other areas of admin interface
            # current_member_and_collab_ids = [person.id for person in Person.objects.all() if person.is_current_member()]
            # filtered_speakers = Person.objects.filter(id__in=current_member_and_collab_ids).order_by('first_name')
            # kwargs["queryset"] = filtered_speakers
            kwargs["widget"] = widgets.FilteredSelectMultiple("speakers", is_stacked=False)
        if db_field.name == "keywords":
            kwargs["widget"] = widgets.FilteredSelectMultiple("keywords", is_stacked=False)
        return super(TalkAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)

class PosterAdmin(admin.ModelAdmin):

    # search_fields are used for auto-complete, see:
    #   https://docs.djangoproject.com/en/3.0/ref/contrib/admin/#django.contrib.admin.ModelAdmin.autocomplete_fields
    search_fields = ['title', 'date']

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        print("PosterAdmin.formfield_for_manytomany: db_field: {} db_field.name {} request: {}".format(db_field, db_field.name, request))
        if db_field.name == "projects":
            kwargs["widget"] = widgets.FilteredSelectMultiple("projects", is_stacked=False)
        if db_field.name == "authors":
            kwargs["widget"] = widgets.FilteredSelectMultiple("authors", is_stacked=False)
        if db_field.name == "keywords":
            kwargs["widget"] = widgets.FilteredSelectMultiple("keywords", is_stacked=False)
        return super(PosterAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)

class ProjectUmbrellaAdmin(admin.ModelAdmin):
    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        if db_field.name == "keywords":
            kwargs["widget"] = widgets.FilteredSelectMultiple("keywords", is_stacked=False)
        return super(ProjectUmbrellaAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)

#from https://stackoverflow.com/questions/9602217/define-an-order-for-manytomanyfield-with-django
#display items inline
class PublicationAuthorInline(admin.TabularInline):
    model = Publication.authors.through
    verbose_name = "Author"
    verbose_name_plural = "Author Order"

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

        # we style the talks select2 widget so that it's wider, see:
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
        #if db_field.name == "authors":
        #    kwargs['widget'] = SortedFilteredSelectMultiple() # removed due to incompatibility with Django 4
        if db_field.name == "projects":
            kwargs["widget"] = widgets.FilteredSelectMultiple("projects", is_stacked=False)
        elif db_field.name == "project_umbrellas":
            kwargs["widget"] = widgets.FilteredSelectMultiple("project umbrellas", is_stacked=False)
        elif db_field.name == "keywords":
            kwargs["widget"] = widgets.FilteredSelectMultiple("keywords", is_stacked=False)
        return super(PublicationAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)

admin.site.register(Person, PersonAdmin)
admin.site.register(Publication, PublicationAdmin)
admin.site.register(Talk, TalkAdmin)
admin.site.register(Project, ProjectAdmin)
admin.site.register(Poster, PosterAdmin)
admin.site.register(Keyword)
admin.site.register(News, NewsAdmin)
admin.site.register(Banner, BannerAdmin)
admin.site.register(Video, VideoAdmin)
admin.site.register(Photo, PhotoAdmin)
admin.site.register(ProjectUmbrella, ProjectUmbrellaAdmin)
admin.site.register(Sponsor)

# For modifying more on the front admin landing page, see https://medium.com/django-musings/customizing-the-django-admin-site-b82c7d325510
admin.site.index_title = f"Makeability Lab Admin. Django version: {django.get_version()} \
    Makeability Lab Website Version: 1.1.4d (fixed cached updates in person) | DEBUG MODE={settings.DEBUG}\
    INTERNAL_IPS={settings.INTERNAL_IPS}"
