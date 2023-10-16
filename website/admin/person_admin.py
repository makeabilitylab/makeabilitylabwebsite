from django.contrib import admin
from website.models import Position, Person, ProjectRole
from website.admin_list_filters import PositionRoleListFilter, PositionTitleListFilter
from image_cropping import ImageCroppingMixin


class PositionInline(admin.StackedInline):
    model = Position

    # This specifies that the Inline is linked to the main owner of the position rather than any of the advisor roles.
    fk_name = "person"

    # This specifies that the field appears only once (by default)
    extra = 0

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # TODO: use Django ORM

        if db_field.name == "advisor" or db_field.name == "co_advisor":
            # Filters advisors to professors and sorts by first name
            # Based on: http://stackoverflow.com/a/30627555
            professor_ids = [person.id for person in Person.objects.all() if person.is_professor]
            filtered_persons = Person.objects.filter(id__in=professor_ids).order_by('first_name')
            # print(filtered_persons, filtered_persons)
            kwargs["queryset"] = filtered_persons

        elif db_field.name == "grad_mentor":
            # Filters grad mentor list to current grad students (either member or collaborator)
            grad_ids = [person.id for person in Person.objects.all() if person.is_grad_student \
                        and (person.is_current_member or person.is_current_collaborator)]
            
            filtered_persons = Person.objects.filter(id__in=grad_ids).order_by('first_name')
            # print(filtered_persons, filtered_persons)
            kwargs["queryset"] = filtered_persons

        return super(PositionInline, self).formfield_for_foreignkey(db_field, request, **kwargs)

class ProjectRoleInline(admin.StackedInline):
    model = ProjectRole
    extra = 0


@admin.register(Person)
class PersonAdmin(ImageCroppingMixin, admin.ModelAdmin):

    # inlines allow us to edit models on the same page as a parent model
    # see: https://docs.djangoproject.com/en/1.11/ref/contrib/admin/#inlinemodeladmin-objects
    inlines = [PositionInline, ProjectRoleInline]

    # The list display lets us control what is shown in the default persons table at Home > Website > People
    # info on displaying multiple entries comes from http://stackoverflow.com/questions/9164610/custom-columns-using-django-admin
    list_display = ('get_full_name', 'get_current_title', 'get_current_role', 'is_active', 
                    'get_start_date', 'get_end_date', 'get_project_count', 'get_pub_count',
                    'get_talk_count', 'get_time_in_current_position', 'get_total_time_as_member')

    list_filter = (PositionRoleListFilter, PositionTitleListFilter)


