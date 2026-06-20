from django.contrib import admin
from website.models import Photo
from image_cropping import ImageCroppingMixin
from website.admin.admin_site import ml_admin_site

@admin.register(Photo, site=ml_admin_site)
class PhotoAdmin(ImageCroppingMixin, admin.ModelAdmin):
    list_display = ('admin_thumbnail', 'caption', 'alt_text', 'project',
                    'get_resolution_as_str', 'cropping', 'picture')

    # The `project` column is an FK; select_related keeps the changelist at a
    # constant query count instead of one extra query per row.
    list_select_related = ('project',)

    # Photos had no search box; search caption/alt text and the owning project.
    search_fields = ['caption', 'alt_text', 'project__name']

    list_per_page = 20 # changes how many images to show on a single admin page