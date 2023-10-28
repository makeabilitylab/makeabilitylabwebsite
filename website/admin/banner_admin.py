from django.contrib import admin
from website.models import Banner
from django.utils.html import format_html
from image_cropping import ImageCroppingMixin

@admin.register(Banner)
class BannerAdmin(ImageCroppingMixin, admin.ModelAdmin):

    # In Django, you can specify the order of fields using one of two methods:
    # - fields, a list of fields you want to display in order
    # - fieldsets, allows you to organize fields into sets
    fieldsets = [
        ('Banner Title and Caption', {'fields': ["title", "caption", "link"]}),
        ('Banner Video', {'fields': ["video"]}),
        ('Banner Image', {'fields': ["image", "alt_text", "cropping"]}),
        ('Banner Pages', {'fields': ["landing_page", "project"]}),
        ('Banner Properties', {'fields': ["favorite", "date_added"]})
        # ('Image', {'fields': ["image", "image_preview"]})
        # ('Image', {'fields': ["image", "cropping"]})
    ]

    # The list display lets us control what is shown in the default persons table at Home > Website > Banners
    # info on displaying multiple entries comes from http://stackoverflow.com/questions/9164610/custom-columns-using-django-admin
    list_display = ('title', 'project', 'landing_page', 'favorite', 'get_media_url')

    autocomplete_fields = ['project']
    readonly_fields = ('date_added',)

    # readonly_fields = ["image_preview"]

    def get_media_url(self, obj):
        """Either returns the video url or the image url, if specified"""
        media_url = obj.image.url if obj.image else obj.video.url if obj.video else None
        return format_html('<a href="{}">{}</a>', media_url, media_url) if media_url else None
        
    get_media_url.short_description = 'Media'