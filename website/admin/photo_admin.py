from django.contrib import admin
from website.models import Photo
from image_cropping import ImageCroppingMixin

@admin.register(Photo)
class PhotoAdmin(ImageCroppingMixin, admin.ModelAdmin):
    list_display = ('__str__', 'admin_thumbnail')