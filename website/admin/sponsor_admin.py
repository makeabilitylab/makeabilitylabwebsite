from django.contrib import admin
from website.models import Sponsor
from image_cropping import ImageCroppingMixin
from django.db.models import Q, Sum
from django.utils import timezone

@admin.register(Sponsor)
class SponsorAdmin(ImageCroppingMixin, admin.ModelAdmin):
    # The list display lets us control what is shown in the default talk table at Home > Website > Sponsors
    # See: https://docs.djangoproject.com/en/dev/ref/contrib/admin/#django.contrib.admin.ModelAdmin.list_display
    list_display = ('name', 'short_name', 'total_funding', 'grant_count', 'active_grant_count')

    def total_funding(self, obj):
        return obj.grant_set.aggregate(total_funding=Sum('funding_amount'))['total_funding']
    total_funding.short_description = 'Total Funding'

    def grant_count(self, obj):
        return obj.grant_set.count()
    grant_count.short_description = 'Grants'

    def active_grant_count(self, obj):
        return obj.grant_set.filter(Q(end_date__isnull=True) | Q(end_date__gt=timezone.now())).count()
    active_grant_count.short_description = 'Active Grants'

