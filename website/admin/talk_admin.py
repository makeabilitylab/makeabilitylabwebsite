from django.contrib import admin
from django.contrib.admin import widgets
from website.models import Talk

@admin.register(Talk)
class TalkAdmin(admin.ModelAdmin):
    # The list display lets us control what is shown in the default talk table at Home > Website > Talk
    # See: https://docs.djangoproject.com/en/dev/ref/contrib/admin/#django.contrib.admin.ModelAdmin.list_display
    list_display = ('title', 'date', 'get_speakers_as_csv', 'forum_name', 'location', 'talk_type')

    # search_fields are used for auto-complete, see:
    #   https://docs.djangoproject.com/en/3.0/ref/contrib/admin/#django.contrib.admin.ModelAdmin.autocomplete_fields
    search_fields = ['title', 'forum_name']

    # fieldsets control how the "add/change" admin views look
    fieldsets = [
        (None,                      {'fields': ['title', 'speakers', 'date']}),
        ('Files',                   {'fields': ['pdf_file', 'raw_file']}),
        ('Talk Venue Info',         {'fields': ['talk_type', 'forum_name', 'forum_url', 'location']}),
        ('Links',                   {'fields': ['video', 'slideshare_url']}),
        ('Project Info',            {'fields': ['projects', 'project_umbrellas']}),
        ('Keyword Info',            {'fields': ['keywords']}),
    ]

    # Filters speakers only to current members and collaborators and sorts by first name
    # Based on: https://stackoverflow.com/a/17457828
    # Update: we no longer do this because sometimes we want to add a talk by a former member or collaborator
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        # print("TalkAdmin.formfield_for_manytomany: db_field: {} db_field.name {} request: {}".format(db_field, db_field.name, request))
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