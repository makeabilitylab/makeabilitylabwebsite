from django.contrib import admin
from website.models import Poster
from website.admin import ArtifactAdmin

@admin.register(Poster)
class PosterAdmin(ArtifactAdmin):

    # search_fields are used for auto-complete, see:
    #   https://docs.djangoproject.com/en/3.0/ref/contrib/admin/#django.contrib.admin.ModelAdmin.autocomplete_fields
    search_fields = ['title', 'date']