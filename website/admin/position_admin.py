from django.contrib import admin
from website.models import Position, Person
from website.models.position import Title
from django.db.models import Q, Case, When, Value, IntegerField
from django.utils import timezone

@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    """Note: We do not want users to edit positions directly. Instead, we want them to edit people and projects.
       See PositionInline in PersonAdmin"""
    def get_model_perms(self, request):
        """
        Return empty perms dict thus hiding the model from admin index.
        """
        return {}
    
    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == "title":
            kwargs['choices'] = sorted(Title.choices, key=lambda choice: Position.TITLE_ORDER_MAPPING[choice[0]])
        return super().formfield_for_choice_field(db_field, request, **kwargs)
    
    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)

        # Check if we're loading the advisor/co-advisor widget. If so
        # we need to filter to professors
        if 'advisor' in request.path or 'co_advisor' in request.path:
           
            # Query the Position model for professor positions
            prof_positions = Position.objects.filter(title__in=Position.get_prof_titles())

            # Get the related Person instance for "Jon Froehlich"
            jon_froehlich = Person.objects.filter(
                                position__in=prof_positions, 
                                first_name="Jon", last_name="Froehlich").distinct()

            # Get today's date
            today = timezone.now().date()

            # Get the related Person instances for the professors who are still active in the lab
            professors = (Person.objects.filter(
                                Q(position__in=prof_positions), # filter to appropriate titles
                                Q(position__start_date__lte=today), # must have started
                                Q(Q(position__end_date__gte=today) | Q(position__end_date__isnull=True))) # must not have ended
                                .order_by('first_name').distinct())

            # Annotate the queryset with a custom order field that is 1 for "Jon Froehlich" and 2 for all other professors
            professors = professors.annotate(
                custom_order=Case(
                    When(first_name="Jon", last_name="Froehlich", then=Value(1)),
                    default=Value(2),
                    output_field=IntegerField(),
                )
            )

            # Order the queryset by the custom order field, then by first name
            professors = professors.order_by('custom_order', 'first_name')

            queryset = professors

        return queryset, use_distinct