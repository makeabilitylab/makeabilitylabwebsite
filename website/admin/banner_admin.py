from django.contrib import admin
from website.models import Banner
from image_cropping import ImageCroppingMixin

@admin.register(Banner)
class BannerAdmin(ImageCroppingMixin, admin.ModelAdmin):

    # In Django, you can specify the order of fields using one of two methods:
    # - fields, a list of fields you want to display in order
    # - fieldsets, allows you to organize fields into sets
    fieldsets = [
        
        ('Banner Image', {'fields': ["image", "alt_text", "cropping"]}),
        ('Banner Video', {'fields': ["video"]}),
        ('Banner Title and Caption', {'fields': ["title", "caption"]}),
        ('Banner Pages', {'fields': ["landing_page", "project"]}),
        ('Banner Properties', {'fields': ["favorite", "date_added"]})
        # ('Image', {'fields': ["image", "image_preview"]})
        # ('Image', {'fields': ["image", "cropping"]})
    ]

    # The list display lets us control what is shown in the default persons table at Home > Website > Banners
    # info on displaying multiple entries comes from http://stackoverflow.com/questions/9164610/custom-columns-using-django-admin
    list_display = ('title', 'project', 'landing_page', 'favorite', 'image')

    autocomplete_fields = ['project']
    readonly_fields = ('date_added',)

    # readonly_fields = ["image_preview"]