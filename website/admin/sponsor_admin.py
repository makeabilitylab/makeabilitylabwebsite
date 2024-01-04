from django.contrib import admin
from website.models import Sponsor
from website.models.sponsor import SPONSOR_THUMBNAIL_SIZE
from image_cropping import ImageCroppingMixin
from django.db.models import Q, Sum
from django.utils import timezone

from django.utils.html import format_html # for formatting thumbnails
from easy_thumbnails.files import get_thumbnailer # for generating thumbnails
import os # for checking if thumbnail file exists

@admin.register(Sponsor)
class SponsorAdmin(ImageCroppingMixin, admin.ModelAdmin):
    # The list display lets us control what is shown in the default talk table at Home > Website > Sponsors
    # See: https://docs.djangoproject.com/en/dev/ref/contrib/admin/#django.contrib.admin.ModelAdmin.list_display
    list_display = ('name', 'get_display_thumbnail', 'short_name', 'total_funding', 
                    'grant_count', 'active_grant_count')
    
    # search_fields is a list of field names that will be searched whenever
    # the user enters a search term in the admin change list page for this model.
    # In this case, the admin will search the 'name' and 'short_name' fields of the Sponsor model.
    search_fields = ['name', 'short_name']

    def total_funding(self, obj):
        return obj.grant_set.aggregate(total_funding=Sum('funding_amount'))['total_funding']
    total_funding.short_description = 'Total Funding'

    def grant_count(self, obj):
        return obj.grant_set.count()
    grant_count.short_description = 'Grants'

    def active_grant_count(self, obj):
        return obj.grant_set.filter(Q(end_date__isnull=True) | Q(end_date__gt=timezone.now())).count()
    active_grant_count.short_description = 'Active Grants'

    def get_display_thumbnail(self, obj):
        if obj.icon and os.path.isfile(obj.icon.path):
            # Use easy_thumbnails to generate a thumbnail
            thumbnailer = get_thumbnailer(obj.icon)
            thumbnail_options = {'size': (SPONSOR_THUMBNAIL_SIZE[0], SPONSOR_THUMBNAIL_SIZE[1]), 'crop': True}
            thumbnail_url = thumbnailer.get_thumbnail(thumbnail_options).url

            return format_html('<img src="{}" height="50" style="border-radius: 5%;"/>', thumbnail_url)
        return 'No Thumbnail'
    
    get_display_thumbnail.short_description = 'Logo'

