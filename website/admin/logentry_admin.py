"""
Read-only admin for Django's ``LogEntry`` audit log.

Django records every add/change/delete performed through the admin in
``django.contrib.admin.models.LogEntry``, but does not surface it anywhere in
the UI—the "Recent actions" sidebar on the index page is deliberately scoped to
the current user's own actions (``{% get_admin_log ... for_user user %}``).

This registers ``LogEntry`` as a fully read-only changelist so a superuser can
browse *everyone's* admin activity, filtered by user, action type, content
type, and date. It is intentionally superuser-only (like Grant/Award) because
it exposes who edited what across all accounts.

The log is append-only by Django and this admin never adds, edits, or deletes
rows; it is purely a viewer.
"""

from django.contrib import admin
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
from django.utils.html import format_html

from website.admin.admin_site import ml_admin_site


@admin.register(LogEntry, site=ml_admin_site)
class LogEntryAdmin(admin.ModelAdmin):
    """Superuser-only, read-only browser over the admin action log."""

    # Newest first—matches the mental model of an activity feed.
    ordering = ('-action_time',)
    date_hierarchy = 'action_time'

    list_display = (
        'action_time',
        'user',
        'action_label',
        'content_type',
        'object_link',
        'change_summary',
    )
    list_filter = ('action_flag', 'content_type', 'user')
    search_fields = ('object_repr', 'change_message', 'user__username',
                     'user__first_name', 'user__last_name')

    # FK columns rendered on every row—join them in the changelist query so we
    # don't fire per-row lookups (#1346).
    list_select_related = ('user', 'content_type')

    @admin.display(description='Action', ordering='action_flag')
    def action_label(self, obj):
        """Human-readable action name with a color cue."""
        label, color = {
            ADDITION: ('Added', '#2e7d32'),
            CHANGE: ('Changed', '#946c00'),
            DELETION: ('Deleted', '#b00020'),
        }.get(obj.action_flag, ('Unknown', '#666'))
        return format_html('<span style="color: {};">{}</span>', color, label)

    @admin.display(description='Object')
    def object_link(self, obj):
        """The affected object as a link to its admin edit page.

        Deletions have no surviving object to link to (and the referenced row
        may be gone), so we fall back to the recorded ``object_repr`` text.
        """
        if obj.action_flag != DELETION:
            try:
                url = obj.get_admin_url()
            except Exception:
                url = None
            if url:
                return format_html('<a href="{}">{}</a>', url, obj.object_repr)
        return obj.object_repr or '—'

    @admin.display(description='Details')
    def change_summary(self, obj):
        """Django's formatted change message (e.g. 'Changed Title and Authors')."""
        message = obj.get_change_message()
        return message or '—'

    # --- Read-only + superuser-only enforcement -------------------------------
    # LogEntry is an append-only audit trail; never allow mutation through here,
    # and restrict all visibility to superusers (this exposes cross-account
    # activity, like Grant/Award).

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_module_permission(self, request):
        return request.user.is_superuser
