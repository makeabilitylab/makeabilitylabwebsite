from django.contrib import admin
from django.utils.html import format_html

from website.models import GrantTrackingLink
from website.admin.admin_site import ml_admin_site


@admin.register(GrantTrackingLink, site=ml_admin_site)
class GrantTrackingLinkAdmin(admin.ModelAdmin):
    """
    Admin for the official grant-tracking bookmarks shown atop the Grant
    changelist (#1448).

    Superuser-only, by the same mechanism as Grant and Award: this model is
    absent from EDITORS_MODELS / CONTRIBUTORS_SPEC in the setup_admin_groups
    management command, so neither group is ever granted its permissions.
    """

    list_display = ('label', 'link', 'notes', 'display_order')
    list_editable = ('display_order',)
    ordering = ('display_order', 'label')

    fieldsets = [
        (None, {
            'fields': ['label', 'url', 'notes', 'display_order'],
            'description': 'Links to the official UW systems that track our grants '
                           '(UW CSE financial reporting, the UW Award Portal, ...). '
                           'They are shown at the top of the Grants page, to superusers only. '
                           'These are stored here rather than in the code because the URLs can '
                           'contain personal sharing tokens and this repository is public.',
        }),
    ]

    @admin.display(description='Link')
    def link(self, obj):
        """Clickable, truncated URL — SharePoint URLs are long enough to blow out
        the changelist column otherwise."""
        display = obj.url if len(obj.url) <= 80 else f"{obj.url[:80]}…"
        return format_html('<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>',
                           obj.url, display)
