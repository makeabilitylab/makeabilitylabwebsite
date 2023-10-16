from django.contrib import admin
from website.models import Photo
from image_cropping import ImageCroppingMixin

@admin.register(Photo)
class PhotoAdmin(ImageCroppingMixin, admin.ModelAdmin):
    list_display = ('admin_thumbnail', 'caption', 'alt_text', 'get_resolution_as_str',
                    'cropping', 'picture')
    
    list_per_page = 20 # changes how many images to show on a single admin page