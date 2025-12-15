# sortedm2m_filter_horizontal_widget - Django 5.x Fixed Version

A fixed/updated version of [django-sortedm2m-filter-horizontal-widget](https://github.com/svleeuwen/sortedm2m-filter-horizontal-widget) that works with Django 5.x.

## What Was Fixed

The original widget had several compatibility issues with Django 5.x:

1. **`build_attrs()` signature** - Updated to match Django 2.0+ API
2. **Deprecated `ADMIN_MEDIA_PREFIX`** - Removed, now uses `STATIC_URL` properly
3. **Media class static paths** - Fixed to use proper Django static file references
4. **jQuery dependency** - Removed jQuery from JavaScript, now uses vanilla JS
5. **CSS image paths** - Replaced `../admin/img/` references with Unicode characters
6. **`render()` signature** - Added `renderer` parameter for Django 4.0+ compatibility

## Installation

1. Copy the `sortedm2m_filter_horizontal_widget` folder to your project

2. Add to `INSTALLED_APPS`:
   ```python
   INSTALLED_APPS = [
       # ...
       'sortedm2m_filter_horizontal_widget',
       # ...
   ]
   ```

3. Run `collectstatic` (for production)

## Usage

```python
from django.contrib import admin
from sortedm2m_filter_horizontal_widget.forms import SortedFilteredSelectMultiple

class PublicationAdmin(admin.ModelAdmin):
    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        if db_field.name == 'authors':
            kwargs['widget'] = SortedFilteredSelectMultiple()
        return super().formfield_for_manytomany(db_field, request, **kwargs)
```

Or with a custom form:

```python
from django import forms
from sortedm2m_filter_horizontal_widget.forms import SortedFilteredSelectMultiple

class PublicationForm(forms.ModelForm):
    class Meta:
        model = Publication
        fields = '__all__'
        widgets = {
            'authors': SortedFilteredSelectMultiple(),
        }
```

## Features

- **Two-panel interface**: Available items on left, chosen items on right
- **Search/filter**: Filter available items by typing
- **Ordering controls**: Up/down buttons to reorder selected items
- **Native Django look**: Matches Django admin's filter_horizontal style
- **Internationalization**: Uses Django's `gettext` for translations
- **Dark mode support**: Works with Django admin dark mode

## Requirements

- Django 4.2+ (tested with 5.2.9)
- django-sortedm2m 4.0.0+

## How It Differs from a Custom Widget

This fixed version preserves the original widget's approach of extending Django admin's built-in filter_horizontal UI. This means:

**Pros:**
- Native Django admin look and feel
- Uses Django's i18n infrastructure
- Handles "Add Related" popup correctly
- Less custom code to maintain

**Cons:**
- Depends on Django admin's JavaScript utilities (`quickElement`, `gettext`)
- Only works in Django admin context (not standalone forms)

If you need a standalone widget that works outside Django admin, consider building a fully custom widget instead.

## License

Same as original: MIT
