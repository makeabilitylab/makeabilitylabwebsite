from django.contrib import admin
from website.models import Banner
from image_cropping import ImageCroppingMixin

@admin.register(Banner)
class BannerAdmin(ImageCroppingMixin, admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ["page", "title", "caption", "alt_text", "link", "favorite", "project"]}),
        # ('Image', {'fields': ["image", "image_preview"]})
        ('Image', {'fields': ["image", "cropping"]})
    ]

    # The list display lets us control what is shown in the default persons table at Home > Website > Banners
    # info on displaying multiple entries comes from http://stackoverflow.com/questions/9164610/custom-columns-using-django-admin
    list_display = ('title', 'project', 'page', 'favorite', 'image')
    # readonly_fields = ["image_preview"]