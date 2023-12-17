from django.contrib import admin
from website.models import Publication

# For lazy translations: https://docs.djangoproject.com/en/4.1/topics/i18n/translation/#lazy-translations
from django.utils.translation import gettext_lazy as _

class PubVenueListFilter(admin.SimpleListFilter):
    """
    This filter allows admin user to filter by a publication's venue type (e.g., conference, journal)

    See: https://docs.djangoproject.com/en/1.11/ref/contrib/admin/#django.contrib.admin.ModelAdmin.list_filter
         https://www.elements.nl/2015/03/16/getting-the-most-out-of-django-admin-filters/
    """

    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = 'publication venue'

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'pub_venue'

    default_value = None

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return (
            ('ASSETS', _('ASSETS')),
            ('CHI', _('CHI')),
            ('IMWUT', _('IMWUT')),
            ('TACCESS', _('TACCESS')),
            ('TEI', _('TEI')),
            ('UIST', _('UIST')),
            ('UbiComp', _('UbiComp'))
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value provided in the pub_venue query string
        Either filtered down to a specific venue or not filtered at all. 
        So, for example: http://localhost:8571/admin/website/publication/?pub_venue=CHI
        would return a filtered queryset of publications that have 'CHI' in their forum_name
        """

        if self.value() is None:
            return queryset
        else:
            return queryset.filter(forum_name__icontains=self.value())