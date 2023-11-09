from django.contrib import admin
from website.models import News, Person, Position
from image_cropping import ImageCroppingMixin
from django.contrib.admin import widgets

from django.db.models import Q
from datetime import date

@admin.register(News)
class NewsAdmin(ImageCroppingMixin, admin.ModelAdmin):

    list_display = ('title', 'author', 'date', 'display_projects', 'display_people') 

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

    # Filters authors only to current members and sorts by firstname
    # Based on: http://stackoverflow.com/a/30627555
    def formfield_for_foreignkey(self, db_field, request, **kwargs):

        # print("NewsAdmin.formfield_for_foreignkey: db_field: {} db_field.name {} request: {}".format(db_field, db_field.name, request))
        if db_field.name == "author":
            # Define the conditions for a current member. Current members need to have:
            # 1. Have started today or in the past
            # 2. Have an end date of null or in the future
            # 3. Be a current member 
            current_member_conditions = (Q(start_date__lte=date.today()) &
                                         (Q(end_date__isnull=True) | Q(end_date__gte=date.today())) &
                                         Q(role=Position.MEMBER)) # must be a member of the lab

            # Get all current members
            current_member_positions = Position.objects.filter(current_member_conditions)

            # Get the related Person objects and sort by first name
            current_members = Person.objects.filter(
                id__in=current_members.values_list('person', flat=True)).order_by('first_name')
            
            kwargs["queryset"] = current_members
        
        return super(NewsAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        if db_field.name == "project":
            kwargs["widget"] = widgets.FilteredSelectMultiple("project", is_stacked=False)
        if db_field.name == "people":
            kwargs["widget"] = widgets.FilteredSelectMultiple("people", is_stacked=False)
        return super(NewsAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)