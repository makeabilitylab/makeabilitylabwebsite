"""
Sorted Filter Horizontal Widget - Django 5.x Compatible Version.

A fixed/updated version of django-sortedm2m-filter-horizontal-widget that works
with Django 5.x. Original: https://github.com/svleeuwen/sortedm2m-filter-horizontal-widget

Changes from original:
- Fixed build_attrs() signature for Django 2.0+ compatibility
- Removed deprecated ADMIN_MEDIA_PREFIX usage
- Fixed Media class to use proper static file references
- Updated render() signature for Django 4.0+ (renderer parameter)
- Added proper JavaScript escaping to prevent XSS vulnerabilities
- Minor code cleanup and Python 3.10+ compatibility

Usage:
    from sortedm2m_filter_horizontal_widget.forms import SortedFilteredSelectMultiple

    class MyModelAdmin(admin.ModelAdmin):
        def formfield_for_manytomany(self, db_field, request=None, **kwargs):
            if db_field.name == 'your_sortedm2m_field_name':
                kwargs['widget'] = SortedFilteredSelectMultiple()
            return super().formfield_for_manytomany(db_field, request, **kwargs)
"""

from django import forms
from django.conf import settings
from django.db.models.query import QuerySet
from django.utils.encoding import force_str
from django.utils.html import conditional_escape, escape, escapejs
from django.utils.safestring import mark_safe


class SortedMultipleChoiceField(forms.ModelMultipleChoiceField):
    """
    A ModelMultipleChoiceField that preserves the order of selected items.

    Works with django-sortedm2m's SortedManyToManyField to maintain
    the order in which items were selected/arranged.

    Example:
        >>> field = SortedMultipleChoiceField(
        ...     queryset=Author.objects.all(),
        ...     is_stacked=False
        ... )
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize the field with an optional is_stacked parameter.

        Args:
            *args: Positional arguments passed to parent class.
            **kwargs: Keyword arguments. Special handling for:
                - is_stacked (bool): If True, stack panels vertically.
                - widget: Custom widget (defaults to SortedFilteredSelectMultiple).
        """
        if not kwargs.get("widget"):
            kwargs["widget"] = SortedFilteredSelectMultiple(
                is_stacked=kwargs.pop("is_stacked", False)
            )
        super().__init__(*args, **kwargs)

    def clean(self, value):
        """
        Clean the field value, preserving the order of selected items.

        Returns a list of model instances in the order they were selected,
        rather than the default queryset ordering.

        Args:
            value: The submitted form value (list of PKs).

        Returns:
            list: Model instances in selection order.
        """
        queryset = super().clean(value)
        if value is None or not isinstance(queryset, QuerySet):
            return queryset
        # Build a dict for O(1) lookup, then return in original order
        object_dict = {str(pk): obj for pk, obj in queryset.in_bulk(value).items()}
        return [object_dict[str(pk)] for pk in value if str(pk) in object_dict]

    def has_changed(self, initial, data):
        """
        Check if the field value has changed, considering order.

        Args:
            initial: Initial value.
            data: Submitted data.

        Returns:
            bool: True if the value or order has changed.
        """
        if initial is None:
            initial = []
        if data is None:
            data = []
        if len(initial) != len(data):
            return True
        initial_list = [force_str(value) for value in self.prepare_value(initial)]
        data_list = [force_str(value) for value in data]
        return data_list != initial_list


class SortedFilteredSelectMultiple(forms.SelectMultiple):
    """
    A SelectMultiple widget with a filter interface and ordering support.

    Displays a two-panel interface similar to Django admin's filter_horizontal,
    but with additional up/down buttons for ordering the selected items.

    The widget automatically includes the necessary static files. It requires
    Django admin's JavaScript utilities (quickElement, gettext) to be loaded,
    which are automatically available in the admin interface.

    Attributes:
        is_stacked: If True, displays panels vertically instead of horizontally.

    Example:
        >>> widget = SortedFilteredSelectMultiple(is_stacked=False)
        >>> # Use in a form
        >>> authors = forms.ModelMultipleChoiceField(
        ...     queryset=Author.objects.all(),
        ...     widget=SortedFilteredSelectMultiple()
        ... )
    """

    class Media:
        """Define static files required by the widget."""

        css = {
            "screen": ("sortedm2m_filter_horizontal_widget/widget.css",)
        }
        js = (
            "sortedm2m_filter_horizontal_widget/OrderedSelectBox.js",
            "sortedm2m_filter_horizontal_widget/OrderedSelectFilter.js",
        )

    def __init__(self, is_stacked=False, attrs=None, choices=()):
        """
        Initialize the widget.

        Args:
            is_stacked: If True, stack panels vertically (default: False).
            attrs: Additional HTML attributes for the select element.
            choices: Initial choices (usually set by the form field).
        """
        self.is_stacked = is_stacked
        super().__init__(attrs, choices)

    def build_attrs(self, base_attrs, extra_attrs=None):
        """
        Build the HTML attributes for the widget.

        Django 2.0+ compatible signature. Adds the 'sortedm2m' class
        and optionally 'stacked' class for styling.

        Args:
            base_attrs: Base attributes from the widget.
            extra_attrs: Additional attributes to merge.

        Returns:
            dict: Merged attributes dictionary.
        """
        attrs = super().build_attrs(base_attrs, extra_attrs)
        classes = attrs.get("class", "").split()
        classes.append("sortedm2m")
        if self.is_stacked:
            classes.append("stacked")
        attrs["class"] = " ".join(classes)
        return attrs

    def render(self, name, value, attrs=None, renderer=None):
        """
        Render the widget HTML.

        Creates a select element and injects JavaScript to transform it
        into the two-panel filter interface with ordering controls.

        Args:
            name: The field name.
            value: Current selected values (list of PKs).
            attrs: Additional HTML attributes.
            renderer: The form renderer (Django 4.0+).

        Returns:
            SafeString: The complete widget HTML including initialization script.
        """
        if attrs is None:
            attrs = {}
        if value is None:
            value = []

        # Get the static URL for admin assets
        static_url = getattr(settings, "STATIC_URL", "/static/")
        admin_static = f"{static_url}admin/"

        # Build the final attributes
        final_attrs = self.build_attrs(self.attrs, attrs)
        final_attrs["name"] = name

        # Generate unique ID
        widget_id = final_attrs.get("id", f"id_{name}")
        final_attrs["id"] = widget_id

        # Build the select element
        output = ['<select multiple="multiple"']
        for attr_name, attr_value in final_attrs.items():
            output.append(f' {attr_name}="{escape(str(attr_value))}"')
        output.append(">")

        # Render options
        options = self.render_options(value)
        if options:
            output.append(options)

        # Determine verbose name for labels
        verbose_name = final_attrs.get("verbose_name", name.split("-")[-1])

        output.append("</select>")

        # Escape values for safe JavaScript insertion (prevents XSS)
        safe_widget_id = escapejs(widget_id)
        safe_verbose_name = escapejs(verbose_name)
        safe_admin_static = escapejs(admin_static)
        is_stacked_js = "true" if self.is_stacked else "false"

        # Add initialization script (runs after page load)
        output.append('<script>window.addEventListener("load", function(e) {')
        output.append(
            f"OrderedSelectFilter.init('{safe_widget_id}', '{safe_verbose_name}', "
            f"{is_stacked_js}, '{safe_admin_static}')"
        )
        output.append("});</script>\n")

        # Add script for handling dynamically added formsets (inlines)
        # This requires jQuery (django.jQuery) which is available in Django admin
        output.append(
            f"""
        <script>
        (function($) {{
            if (!$) return;  // Guard against missing jQuery
            $(document).ready(function() {{
                var updateOrderedSelectFilter = function() {{
                    if (typeof OrderedSelectFilter !== "undefined") {{
                        $(".sortedm2m").each(function(index, value) {{
                            // Skip if already initialized (has _from suffix)
                            if (value.id.endsWith('_from')) return;
                            var namearr = value.name.split('-');
                            OrderedSelectFilter.init(value.id, namearr[namearr.length-1], false, '{safe_admin_static}');
                        }});
                        $(".sortedm2mstacked").each(function(index, value) {{
                            if (value.id.endsWith('_from')) return;
                            var namearr = value.name.split('-');
                            OrderedSelectFilter.init(value.id, namearr[namearr.length-1], true, '{safe_admin_static}');
                        }});
                    }}
                }};
                $(document).on('formset:added', function(event, $row, formsetName) {{
                    updateOrderedSelectFilter();
                }});
            }});
        }})(django.jQuery);
        </script>"""
        )

        return mark_safe("\n".join(output))

    def render_option(self, selected_choices, option_value, option_label):
        """
        Render a single option element.

        Adds a data-sort-value attribute for selected options to preserve
        their order when the widget initializes.

        Args:
            selected_choices: List of currently selected values (as strings).
            option_value: The option's value.
            option_label: The option's display label.

        Returns:
            str: HTML for the option element.
        """
        option_value_str = force_str(option_value)
        escaped_value = escape(option_value_str)
        escaped_label = conditional_escape(force_str(option_label))

        # Check if selected and get sort order
        if option_value_str in selected_choices:
            selected_html = ' selected="selected"'
            try:
                # Use the string version for index lookup to match the list
                index = selected_choices.index(option_value_str)
                selected_html = f' data-sort-value="{index}"{selected_html}'
            except ValueError:
                pass
        else:
            selected_html = ""

        return f'<option value="{escaped_value}"{selected_html}>{escaped_label}</option>'

    def render_options(self, selected_choices):
        """
        Render all option elements.

        Args:
            selected_choices: List of currently selected values.

        Returns:
            str: HTML for all option elements.
        """
        # Normalize selected choices to strings
        selected_choices = [force_str(v) for v in (selected_choices or [])]

        output = []
        for option_value, option_label in self.choices:
            if isinstance(option_label, (list, tuple)):
                # Handle optgroups
                output.append(f'<optgroup label="{escape(force_str(option_value))}">')
                for sub_value, sub_label in option_label:
                    output.append(self.render_option(selected_choices, sub_value, sub_label))
                output.append("</optgroup>")
            else:
                output.append(
                    self.render_option(selected_choices, option_value, option_label)
                )
        return "\n".join(output)

    def has_changed(self, initial, data):
        """
        Check if the field value has changed, considering order.

        Unlike the default implementation which only checks set membership,
        this also checks if the order has changed.

        Args:
            initial: Initial value.
            data: Submitted data.

        Returns:
            bool: True if the value or order has changed.
        """
        if initial is None:
            initial = []
        if data is None:
            data = []
        if len(initial) != len(data):
            return True
        initial_list = [force_str(value) for value in initial]
        data_list = [force_str(value) for value in data]
        return data_list != initial_list