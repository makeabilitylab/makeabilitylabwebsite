from django.contrib import admin
from django.contrib.admin import widgets
from website.models import Project, ProjectUmbrella
from website.admin.admin_site import ml_admin_site

# To display a list of all projects associated with a specific ProjectUmbrella when you click on it 
# in the Django admin interface, you can use Django’s InlineModelAdmin objects. 
class ProjectInline(admin.TabularInline):  # or admin.StackedInline
    model = Project.project_umbrellas.through

@admin.register(ProjectUmbrella, site=ml_admin_site)
class ProjectUmbrellaAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name', 'project_count')
    inlines = [ProjectInline]

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        if db_field.name == "keywords":
            kwargs["widget"] = widgets.FilteredSelectMultiple("keywords", is_stacked=False)

        return super(ProjectUmbrellaAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)