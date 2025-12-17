from django.contrib import admin
from website.models import Position, Person
from website.models.position import Title
from website.admin.utils import get_active_professors_queryset

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
        """
        Customize autocomplete search results for advisor fields.
        
        When the autocomplete is triggered from an advisor or co_advisor field,
        filters results to show only active professors.
        """
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)

        if 'advisor' in request.path or 'co_advisor' in request.path:
            queryset = get_active_professors_queryset()

        return queryset, use_distinct