from django.contrib import admin
from django.contrib.admin import widgets
from website.models import Project, ProjectHeader, Banner, Photo
from website.models.project import PROJECT_THUMBNAIL_SIZE
from website.admin_list_filters import ActiveProjectsFilter
from image_cropping import ImageCroppingMixin

from django.utils.html import format_html # for formatting thumbnails
from easy_thumbnails.files import get_thumbnailer # for generating thumbnails
import os # for checking if thumbnail file exists

class ProjectHeaderInline(ImageCroppingMixin, admin.StackedInline):
    """This allows us to edit ProjectHeader from the Project page"""
    model = ProjectHeader
    extra = 0

class BannerInline(ImageCroppingMixin, admin.StackedInline):
    """This allows us to edit Banner from the Project page"""
    model = Banner
    extra = 0  # Number of extra "empty" forms to show at the bottom

class PhotoInline(ImageCroppingMixin, admin.StackedInline):
    """This allows us to add Photos from the Project page"""
    model = Photo
    extra = 0  # Number of extra "empty" forms to show at the bottom

@admin.register(Project)
class ProjectAdmin(ImageCroppingMixin, admin.ModelAdmin):
    search_fields = ['name']  # allows you to search by the name of the project
    inlines = [ProjectHeaderInline, BannerInline, PhotoInline]

    # The list display lets us control what is shown in the Project table at Home > Website > Project
    # info on displaying multiple entries comes from http://stackoverflow.com/questions/9164610/custom-columns-using-django-admin
    list_display = ('name', 'get_display_thumbnail', 'start_date', 'end_date', 'has_ended', 
                    'get_contributor_count', 'get_people_count',
                    'get_current_member_count', 'get_past_member_count',
                    'get_most_recent_artifact_date', 'get_most_recent_artifact_type',
                    'get_publication_count', 'get_video_count', 'get_talk_count', 'get_banner_count')
    
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

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        if db_field.name == "sponsors":
            kwargs["widget"] = widgets.FilteredSelectMultiple("sponsors", is_stacked=False)
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
