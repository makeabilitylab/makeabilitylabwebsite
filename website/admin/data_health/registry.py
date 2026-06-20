"""
Lightweight registry + base class for read-only "Data Health" admin checks.

Each check subclasses :class:`HealthCheck` and is registered with
``@register_check``. The admin dashboard (website/admin/data_health/views.py)
iterates :data:`REGISTRY` to show a flagged-row count per check; each check
renders a detail table and a CSV download generated on the fly.

Checks MUST be strictly read-only — never call ``.save()`` or mutate the DB.
"""

import csv
import io

from django.http import HttpResponse
from django.utils import timezone


class HealthCheck:
    """
    Base class for a single read-only data-health check.

    Subclasses set the class attributes below and implement :meth:`get_rows`,
    returning a list of dicts keyed by the entries in :attr:`columns`.
    """

    #: URL-safe identifier, e.g. ``"duplicate-people"``.
    slug = ''
    #: Human-readable title shown on the dashboard and detail page.
    title = ''
    #: One-line description of what the check surfaces.
    description = ''
    #: Dashboard grouping, e.g. ``"People"`` / ``"Artifacts"`` / ``"Projects"``.
    group = 'Other'
    #: Ordered column keys; used as table headers and the CSV header row.
    columns = []

    def get_rows(self):
        """Return a list of row dicts (read-only). Override in subclasses."""
        raise NotImplementedError

    def row_link(self, row):
        """Optional: a ``(label, url)`` pair to act on ``row`` from the detail
        page, or ``None``. Lets a check wire its read-only findings to a fixer
        elsewhere in the admin (e.g. the keyword-merge changelist). Default: no
        link. Only affects the on-screen table — the CSV export is unchanged.
        """
        return None

    def count(self):
        """Number of flagged rows. Override for a cheaper count if available."""
        return len(self.get_rows())


# Ordered list of registered checks, plus a slug -> instance lookup.
REGISTRY = []
_REGISTRY_BY_SLUG = {}


def register_check(check_cls):
    """Class decorator: instantiate a HealthCheck subclass and register it."""
    instance = check_cls()
    if not instance.slug:
        raise ValueError(f"{check_cls.__name__} must define a non-empty slug")
    if instance.slug in _REGISTRY_BY_SLUG:
        raise ValueError(f"Duplicate data-health check slug: {instance.slug}")
    REGISTRY.append(instance)
    _REGISTRY_BY_SLUG[instance.slug] = instance
    return check_cls


def get_check(slug):
    """Return the registered check instance for ``slug``, or None."""
    return _REGISTRY_BY_SLUG.get(slug)


def rows_to_csv_response(check):
    """
    Render ``check``'s rows as a downloadable CSV ``HttpResponse``.

    The CSV is built in memory and streamed through the (authenticated)
    response, so it never touches a web-served path on disk.
    """
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=check.columns, extrasaction='ignore')
    writer.writeheader()
    for row in check.get_rows():
        writer.writerow(row)

    today = timezone.now().date().isoformat()
    response = HttpResponse(buffer.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{check.slug}-{today}.csv"'
    return response
