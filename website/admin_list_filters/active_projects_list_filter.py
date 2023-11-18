from django.contrib import admin

# For lazy translations: https://docs.djangoproject.com/en/4.1/topics/i18n/translation/#lazy-translations
from django.utils.translation import gettext_lazy as _

class ActiveProjectsFilter(admin.SimpleListFilter):
    """
    This filter allows admin user to filter by whether a project is active or not
    """

    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = 'project status'

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'active_project_status'

    default_value = 'Active'

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return (
            ('All', _('All')), 
            ('Active', _('Active')),
            ('Archived', _('Archived')),
        )
    
    def choices(self, cl):
        for lookup, title in self.lookup_choices:
            yield {
                'selected': self.value() == lookup,
                'query_string': cl.get_query_string({
                    self.parameter_name: lookup,
                }, []),
                'display': title,
            }

    def queryset(self, request, queryset):
        """
        Returns either an "active" projects queryset or an "archived" projects queryset
        """
        # print("queryset: self.value() = {} with type = {}".format(self.value(), type(self.value())))
        
        if self.value() == 'Active' or self.value() == None:
            return queryset.filter(end_date__isnull=True)
        elif self.value() == 'Archived':
            return queryset.filter(end_date__isnull=False)
        else:
            return queryset