from django.contrib import admin
from website.models import Poster
from django.contrib.admin import widgets

@admin.register(Poster)
class PosterAdmin(admin.ModelAdmin):

    # search_fields are used for auto-complete, see:
    #   https://docs.djangoproject.com/en/3.0/ref/contrib/admin/#django.contrib.admin.ModelAdmin.autocomplete_fields
    search_fields = ['title', 'date']

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "projects":
            kwargs["widget"] = widgets.FilteredSelectMultiple("projects", is_stacked=False)
        if db_field.name == "authors":
            kwargs["widget"] = widgets.FilteredSelectMultiple("authors", is_stacked=False)
        if db_field.name == "keywords":
            kwargs["widget"] = widgets.FilteredSelectMultiple("keywords", is_stacked=False)
            
        return super(PosterAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)