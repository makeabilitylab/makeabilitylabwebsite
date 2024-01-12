from django.contrib import admin
from website.models import Position
from website.models.position import Title

class PositionTitleListFilter(admin.SimpleListFilter):
    """
    This filter allows admin user to filter by a person's title.

    See: https://docs.djangoproject.com/en/1.11/ref/contrib/admin/#django.contrib.admin.ModelAdmin.list_filter
         https://www.elements.nl/2015/03/16/getting-the-most-out-of-django-admin-filters/
    """

    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = 'position'

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'position_title'

    default_value = None

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return Title.choices

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        from django.db.models import Subquery, OuterRef

        # Get the latest position for each person
        latest_position = Position.objects.filter(person_id=OuterRef('pk')).order_by('-start_date')
        queryset = queryset.annotate(
            latest_position_title=Subquery(latest_position.values('title')[:1])
        )

        if self.value() is None:
            return queryset
        elif self.value() == Title.UNKNOWN:
            return queryset.filter(latest_position_title__isnull=True)
        else:
            return queryset.filter(latest_position_title=self.value())