from django.contrib import admin
from django.contrib.admin import widgets
from website.models import Project, Banner, Photo, ProjectRole, Grant
from website.models.project import PROJECT_THUMBNAIL_SIZE
from website.admin_list_filters import ActiveProjectsFilter
from image_cropping import ImageCroppingMixin

from django.utils.html import format_html # for formatting thumbnails
from easy_thumbnails.files import get_thumbnailer # for generating thumbnails
import os # for checking if thumbnail file exists
from django import forms
from django.db.models import F

class ProjectRoleInline(admin.TabularInline):
    model = ProjectRole
    extra = 1  # Number of extra forms displayed

    autocomplete_fields = ['person']

    # This method is used to customize the form field for a given database field
    def formfield_for_dbfield(self, db_field, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, **kwargs)
        # If the database field is 'role', we create a new Textarea widget with the desired 
        # number of columns and rows
        if db_field.name == 'role':
            formfield.widget = forms.Textarea(attrs={'cols': '40', 'rows': '2'})
        return formfield
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Order by end_date descending with nulls first
        return qs.order_by(F('end_date').desc(nulls_first=True))

class BannerInline(ImageCroppingMixin, admin.StackedInline):
    """This allows us to edit Banner from the Project page"""
    model = Banner
    extra = 1  # Number of extra "empty" forms to show at the bottom

class PhotoInline(ImageCroppingMixin, admin.StackedInline):
    """This allows us to add Photos from the Project page"""
    model = Photo
    extra = 0  # Number of extra "empty" forms to show at the bottom

class GrantInline(admin.TabularInline):
    model = Grant.projects.through
    extra = 1

@admin.register(Project)
class ProjectAdmin(ImageCroppingMixin, admin.ModelAdmin):
    search_fields = ['name']  # allows you to search by the name of the project
    inlines = [GrantInline, BannerInline, PhotoInline, ProjectRoleInline]

    # The list display lets us control what is shown in the Project table at Home > Website > Project
    # info on displaying multiple entries comes from http://stackoverflow.com/questions/9164610/custom-columns-using-django-admin
    list_display = ('name', 'get_display_thumbnail', 'start_date', 'end_date', 'has_ended', 
                    'get_contributor_count', 'get_people_count',
                    'get_current_member_count', 'get_past_member_count',
                    'get_most_recent_artifact_date', 'get_most_recent_artifact_type',
                    'get_publication_count', 'get_video_count', 'get_talk_count', 'get_banner_count')
    
    fieldsets = [
        (None,                      {'fields': ['name', 'short_name']}),
        ('About',                   {'fields': ['start_date', 'end_date', 'summary', 'about', 'gallery_image', 'cropping', 'thumbnail_alt_text']}),
        ('Links',                   {'fields': ['website', 'data_url', 'featured_video', 'featured_code_repo_url']}),
        ('Associations',            {'fields': ['project_umbrellas', 'keywords']}),
    ]
    
    list_filter = (ActiveProjectsFilter, )

    def get_display_thumbnail(self, obj):
        if obj.gallery_image and os.path.isfile(obj.gallery_image.path):
            # Use easy_thumbnails to generate a thumbnail
            thumbnailer = get_thumbnailer(obj.gallery_image)
            thumbnail_options = {'size': (PROJECT_THUMBNAIL_SIZE[0], PROJECT_THUMBNAIL_SIZE[1]), 'crop': True}
            thumbnail_url = thumbnailer.get_thumbnail(thumbnail_options).url

            return format_html('<img src="{}" height="50" style="border-radius: 5%;"/>', thumbnail_url)
        return 'No Thumbnail'
    
    get_display_thumbnail.short_description = 'Thumbnail'

    def get_search_results(self, request, queryset, search_term):
        """In this code, get_search_results is a method that Django calls to get the list of results 
        for the autocomplete dropdown. By overriding this method, you can modify the queryset that 
        Django uses to populate the dropdown. The line queryset = queryset.order_by('name') sorts 
        the projects by name"""
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        queryset = queryset.order_by('name')
        return queryset, use_distinct

    def formfield_for_dbfield(self, db_field, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, **kwargs)
        if db_field.name == 'summary':
            formfield.widget = forms.Textarea(attrs={'rows': 3, 'class': 'vLargeTextField'})
        return formfield

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        if db_field.name == "keywords":
            kwargs["widget"] = widgets.FilteredSelectMultiple("keywords", is_stacked=False)
        if db_field.name == "project_umbrellas":
            kwargs["widget"] = widgets.FilteredSelectMultiple("project umbrellas", is_stacked=False)
        return super(ProjectAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)
    
    def changelist_view(self, request, extra_context=None):
        if not request.GET:
            q = request.GET.copy()
            q['active_project_status'] = 'Active'
            request.GET = q
            request.META['QUERY_STRING'] = request.GET.urlencode()
        return super(ProjectAdmin,self).changelist_view(request, extra_context=extra_context)
