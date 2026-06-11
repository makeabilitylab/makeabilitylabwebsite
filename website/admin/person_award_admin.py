from django.contrib import admin
from website.models import PersonAward
from website.admin.admin_site import ml_admin_site


@admin.register(PersonAward, site=ml_admin_site)
class PersonAwardAdmin(admin.ModelAdmin):
    # Controls the columns shown in the change list at Home > Website > Person awards.
    # get_recipient_names is a method on the PersonAward model; its column header
    # comes from that method's short_description ("Recipients").
    list_display = ('title', 'organization', 'date', 'get_recipient_names', 'award_type')

    list_filter = ('award_type', 'date')

    search_fields = ('title', 'organization',
                     'recipients__first_name', 'recipients__last_name')

    ordering = ('-date',)

    # NOTE: `recipients` is a SortedManyToManyField, so it renders with sortedm2m's
    # default ordered widget out of the box. If you'd rather match the filter-horizontal
    # widget used for authors elsewhere (the repo's sortedm2m_filter_horizontal_widget),
    # set the appropriate formfield_overrides / widget here to match person_admin.py.
