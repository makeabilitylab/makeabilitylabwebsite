from django.contrib import admin
from website.models import Sponsor
from image_cropping import ImageCroppingMixin

@admin.register(Sponsor)
class SponsorAdmin(ImageCroppingMixin, admin.ModelAdmin):
    pass