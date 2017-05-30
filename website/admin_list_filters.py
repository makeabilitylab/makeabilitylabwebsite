from django.contrib import admin
from website.models import Person, Position
from django.utils.translation import ugettext_lazy as _

class CurrentMemberListFilter(admin.SimpleListFilter):

    """
    This filter allows admin user to filter by member status. Default is current members
    
    See: https://docs.djangoproject.com/en/1.11/ref/contrib/admin/#django.contrib.admin.ModelAdmin.list_filter
         https://www.elements.nl/2015/03/16/getting-the-most-out-of-django-admin-filters/
    """

    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = 'current member status'

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'current_member_status'

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
            (None, _('Current')), #default, see https://stackoverflow.com/a/16556771
            ('Past', _('Past')),
            ('All', _('All'))
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

        print("queryset: self.value() = {} with type = {}".format(self.value(), type(self.value())))

        # Compare the requested value (either True or False)
        # to decide how to filter the queryset.

        filtered_person_ids = []
        for person in Person.objects.all():
            if person.is_current_member() is True:
                print("{} is_current_member(): {} | self.value(): {} | equals? {} | type(member): {} | type(self.value): {}".format(person.get_full_name(),
                                                                                      person.is_current_member(), self.value(),
                                                                                      person.is_current_member() is self.value(),
                                                                                      type(person.is_current_member()),
                                                                                      type(self.value())))
            if person.is_current_member() is True and self.value() is None:
                filtered_person_ids.append(person.id)
            elif person.is_current_member() is False and self.value() == "Past":
                filtered_person_ids.append(person.id)
            elif self.value() == "All":
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


class PositionListFilter(admin.SimpleListFilter):
    """
    This filter allows admin user to filter by a person's position. 

    See: https://docs.djangoproject.com/en/1.11/ref/contrib/admin/#django.contrib.admin.ModelAdmin.list_filter
         https://www.elements.nl/2015/03/16/getting-the-most-out-of-django-admin-filters/
    """

    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = 'position'

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'position'

    default_value = None

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return Position.TITLE_CHOICES

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """

        print("queryset: self.value() = {} with type = {}".format(self.value(), type(self.value())))

        filtered_person_ids = []
        for person in Person.objects.all():
            cur_position = person.get_latest_position()
            if self.value() is None:
                filtered_person_ids.append(person.id)
            elif cur_position is not None and cur_position.title == self.value() or \
                cur_position is None and self.value() == Position.UNKNOWN:
                filtered_person_ids.append(person.id)

        return queryset.filter(id__in=filtered_person_ids)