from django.contrib import admin
from website.models import Person

# For lazy translations: https://docs.djangoproject.com/en/4.1/topics/i18n/translation/#lazy-translations
from django.utils.translation import gettext_lazy as _

class PositionRoleListFilter(admin.SimpleListFilter):

    """
    This filter allows admin user to filter by position status. Default is current members
    
    See: https://docs.djangoproject.com/en/1.11/ref/contrib/admin/#django.contrib.admin.ModelAdmin.list_filter
         https://www.elements.nl/2015/03/16/getting-the-most-out-of-django-admin-filters/
    """

    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = 'Role'

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'position_role'

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
            (None, _('Current member')), #default, see https://stackoverflow.com/a/16556771
            ('graduated_phd_student', _('Graduated PhD student')),
            ('past_member', _('Past member')),
            ('current_collaborator', _('Current collaborator')),
            ('past_collaborator', _('Past collaborator')),
            ('other', _('Other')),
            ('all', _('All'))
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
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        
        # Compare the requested value (either True or False)
        # to decide how to filter the queryset.
        filtered_person_ids = []
        for person in Person.objects.all():
            if person.is_current_member is True and self.value() is None:
                filtered_person_ids.append(person.id)
            elif person.is_alumni_member is True and person.is_current_member is False and self.value() == "past_member":
                filtered_person_ids.append(person.id)
            elif person.is_current_collaborator is True and self.value() == "current_collaborator":
                filtered_person_ids.append(person.id)
            elif person.is_past_collaborator is True and self.value() == "past_collaborator":
                filtered_person_ids.append(person.id)
            elif person.is_current_member is False and person.is_alumni_member is False and\
                    person.is_current_collaborator is False and person.is_past_collaborator is False and\
                    self.value() == "other":
                filtered_person_ids.append(person.id)
            elif self.value() == "all":
                filtered_person_ids.append(person.id)

            # also check for graduated phd students
            if self.value() == "graduated_phd_student" and person.is_graduated_phd_student:
                filtered_person_ids.append(person.id)

        return queryset.filter(id__in = filtered_person_ids)


    # def value(self):
    #     """
    #     Overriding this method will allow us to always have a default value.
    #     """
        # value = super(SpeciesListFilter, self).value()
        # if value is None:
        #     if self.default_value is None:
        #         # If there is at least one Species, return the first by name. Otherwise, None.
        #         first_species = Species.objects.order_by('name').first()
        #         value = None if first_species is None else first_species.id
        #         self.default_value = value
        #     else:
        #         value = self.default_value
        # return str(value)