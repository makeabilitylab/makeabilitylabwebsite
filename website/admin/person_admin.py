from django.contrib import admin
from website.models import Position, Person, ProjectRole
from website.admin_list_filters import PositionRoleListFilter, PositionTitleListFilter
from image_cropping import ImageCroppingMixin

from django.db.models import Q
from django.utils import timezone


class PositionInline(admin.StackedInline):
    model = Position

    # This specifies that the Inline is linked to the main owner of the position rather than any of the advisor roles.
    fk_name = "person"

    # This specifies that the field appears only once (by default)
    extra = 0

    def formfield_for_foreignkey(self, db_field, request, **kwargs):

        # Check if we're loading the advisor/co-advisor widget. If so
        # we need to filter to professors
        if db_field.name == "advisor" or db_field.name == "co_advisor":
           
            # Query the Position model
            prof_positions = Position.objects.filter(title__in=Position.get_prof_titles())

            # Get the related Person instances
            professors = Person.objects.filter(position__in=prof_positions).order_by('first_name').distinct()

            kwargs["queryset"] = professors

        elif db_field.name == "grad_mentor":
            # Define the titles we are interested in
            titles = [Position.POST_DOC, Position.PHD_STUDENT, Position.MS_STUDENT, 
                Position.RESEARCH_SCIENTIST, Position.SOFTWARE_DEVELOPER, Position.DESIGNER]

            # Get today's date
            today = timezone.now().date()

            # Query the database
            grad_mentors = (Person.objects.filter(
                        Q(position__title__in=titles), # filter to appropriate titles
                        Q(position__start_date__lte=today), # must have started
                        Q(Q(position__end_date__gte=today) | Q(position__end_date__isnull=True))) # must not have ended
                        .order_by('first_name').distinct())

            kwargs["queryset"] = grad_mentors

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


