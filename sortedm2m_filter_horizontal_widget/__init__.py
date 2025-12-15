"""
sortedm2m_filter_horizontal_widget - Django 5.x Compatible Version

A filter horizontal widget for django-sortedm2m that provides a two-panel
interface for selecting and ordering many-to-many relationships.

Usage:
    from sortedm2m_filter_horizontal_widget.forms import SortedFilteredSelectMultiple

    class MyModelAdmin(admin.ModelAdmin):
        def formfield_for_manytomany(self, db_field, request=None, **kwargs):
            if db_field.name == 'your_sortedm2m_field_name':
                kwargs['widget'] = SortedFilteredSelectMultiple()
            return super().formfield_for_manytomany(db_field, request, **kwargs)
"""

from .forms import SortedFilteredSelectMultiple, SortedMultipleChoiceField

__all__ = ['SortedFilteredSelectMultiple', 'SortedMultipleChoiceField']
__version__ = '2.0.1'
