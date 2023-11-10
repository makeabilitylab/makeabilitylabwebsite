from django.contrib import admin
from website.models import Publication

class PubVenueTypeListFilter(admin.SimpleListFilter):
    """
    This filter allows admin user to filter by a publication's venue type (e.g., conference, journal)

    See: https://docs.djangoproject.com/en/1.11/ref/contrib/admin/#django.contrib.admin.ModelAdmin.list_filter
         https://www.elements.nl/2015/03/16/getting-the-most-out-of-django-admin-filters/
    """

    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = 'publication venue type'

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'pub_venue_type'

    default_value = None

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return Publication.PUB_VENUE_TYPE_CHOICES

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value provided in the pub_venue_type query string
        Either filtered down to a specific venue type or not filtered at all. 
        So, for example: http://localhost:8571/admin/website/publication/?pub_venue_type=Journal
        would return a filtered queryset of publications that have a pub_venue_type of `Journal`
        """

        if self.value() is None:
            return queryset
        else:
            return queryset.filter(pub_venue_type=self.value())
