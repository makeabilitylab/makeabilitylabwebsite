from django.contrib import admin
from website.models import News, Person, Position
from image_cropping import ImageCroppingMixin
from django.contrib.admin import widgets

from django.db.models import Q
from datetime import date

from django.db.models.functions import TruncYear # for filtering by year

class YearListFilter(admin.SimpleListFilter):
    title = 'year' # a label for our filter
    parameter_name = 'year' # you can put anything here

    def lookups(self, request, model_admin):
        # This method should return a list of tuples. The first element in each
        # tuple is the coded value for the option that will appear in the URL query.
        # The second element is the human-readable name for the option that will
        # appear in the right sidebar.
       
        qs = model_admin.model.objects.annotate(year=TruncYear('date')).values('year').distinct()
        return [(x['year'].year, x['year'].year) for x in qs.order_by('-year')]

    def queryset(self, request, queryset):
        # This method is used when the user selects a choice.
        # It should return a filtered queryset based on the chosen value.
        if self.value():
            return queryset.filter(date__year=self.value())

@admin.register(News)
class NewsAdmin(ImageCroppingMixin, admin.ModelAdmin):

    # The list display lets us control what is shown in the default table at Home > Website > News
    list_display = ('title', 'author', 'date', 'display_projects', 'display_people') 

    # Add a filter to the right sidebar that allows us to filter by year
    list_filter = (YearListFilter, 'project')

    # Define 'author' as an auto-complete field. We must then also define "search_fields"
    # in PersonAdmin or we'll receive a Django error
    autocomplete_fields = ['author']

    # Exclude the slug field since it is auto-generated
    exclude = ('slug',)

    def display_projects(self, obj):
        """Displays the projects linked to the news story"""
        return ", ".join([project.name for project in obj.project.all()])
    
    display_projects.short_description = 'Projects'

    def display_people(self, obj):
        """Displays the people linked to the news story"""
        return ", ".join([person.get_full_name() for person in obj.people.all()])
    display_people.short_description = 'People'

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        if db_field.name == "project":
            kwargs["widget"] = widgets.FilteredSelectMultiple("project", is_stacked=False)
        if db_field.name == "people":
            kwargs["widget"] = widgets.FilteredSelectMultiple("people", is_stacked=False)
        return super(NewsAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)
    
    def queryset(self, request, queryset):
        # This method is used when the user selects a choice.
        # It should return a filtered queryset based on the chosen value.
        if self.value():
            return queryset.filter(date__year=self.value())