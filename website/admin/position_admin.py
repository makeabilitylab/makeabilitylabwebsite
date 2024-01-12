from django.contrib import admin
from website.models import Position
from website.models.position import Title

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