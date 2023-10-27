from django.contrib import admin
from website.models import News, Person
from image_cropping import ImageCroppingMixin
from django.contrib.admin import widgets

@admin.register(News)
class NewsAdmin(ImageCroppingMixin, admin.ModelAdmin):

    list_display = ('title', 'author', 'date', 'display_projects', 'display_people') 

    # Exclude the slug field since it is auto-generated
    exclude = ('slug',)

    def display_projects(self, obj):
        return ", ".join([project.name for project in obj.project.all()])
    
    display_projects.short_description = 'Projects'

    def display_people(self, obj):
        return ", ".join([person.get_full_name() for person in obj.people.all()])
    display_people.short_description = 'Authors'

    # Filters authors only to current members and sorts by firstname
    # Based on: http://stackoverflow.com/a/30627555
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # print("NewsAdmin.formfield_for_foreignkey: db_field: {} db_field.name {} request: {}".format(db_field, db_field.name, request))
        if db_field.name == "author":
            current_member_ids = [person.id for person in Person.objects.all() if person.is_current_member]
            filtered_persons = Person.objects.filter(id__in=current_member_ids).order_by('first_name')
            #print("filtered_persons", filtered_persons)
            kwargs["queryset"] = filtered_persons
        return super(NewsAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        if db_field.name == "project":
            kwargs["widget"] = widgets.FilteredSelectMultiple("project", is_stacked=False)
        if db_field.name == "people":
            kwargs["widget"] = widgets.FilteredSelectMultiple("people", is_stacked=False)
        return super(NewsAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)