from django.contrib import admin
from website.models import Video

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    # The list display lets us control what is shown in the default persons table at Home > Website > Videos
    # info on displaying multiple entries comes from http://stackoverflow.com/questions/9164610/custom-columns-using-django-admin
    list_display = ('title', 'date', 'caption', 'project')

    # search_fields are used for auto-complete, see:
    #   https://docs.djangoproject.com/en/3.0/ref/contrib/admin/#django.contrib.admin.ModelAdmin.autocomplete_fields
    search_fields = ['title', 'get_video_host_str', 'date']

    # default the sort order in table to descending order by date
    ordering = ('-date',)