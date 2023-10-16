from django.contrib import admin
from django.contrib.admin import widgets
from website.models import Project, ProjectHeader, Banner, Photo
from website.admin_list_filters import ActiveProjectsFilter
from image_cropping import ImageCroppingMixin

class ProjectHeaderInline(ImageCroppingMixin, admin.StackedInline):
    """This allows us to edit ProjectHeader from the Project page"""
    model = ProjectHeader
    extra = 0

class BannerInline(admin.TabularInline):
    """This allows us to edit Banner from the Project page"""
    model = Banner
    extra = 0  # Number of extra "empty" forms to show at the bottom

class PhotoInline(admin.TabularInline):
    """This allows us to add Photos from the Project page"""
    model = Photo
    extra = 0  # Number of extra "empty" forms to show at the bottom

@admin.register(Project)
class ProjectAdmin(ImageCroppingMixin, admin.ModelAdmin):
    inlines = [ProjectHeaderInline, BannerInline, PhotoInline]

    # The list display lets us control what is shown in the Project table at Home > Website > Project
    # info on displaying multiple entries comes from http://stackoverflow.com/questions/9164610/custom-columns-using-django-admin
    list_display = ('name', 'start_date', 'end_date', 'has_ended', 'get_people_count',
                    'get_current_member_count', 'get_past_member_count',
                    'get_most_recent_artifact_date', 'get_most_recent_artifact_type',
                    'get_publication_count', 'get_video_count', 'get_talk_count')
    
    list_filter = (ActiveProjectsFilter, )

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