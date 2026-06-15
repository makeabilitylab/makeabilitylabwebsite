"""
Read-only, superuser-gated admin views for the Data Health dashboard.

Wired into the admin URLconf by ``MakeabilityLabAdminSite.get_urls()``
(website/admin/admin_site.py). ``self.admin_view`` already enforces staff +
login; these views additionally require ``is_superuser`` because the
underlying checks expose personal data (e.g. member emails).
"""

from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import render

from website.admin.data_health.registry import REGISTRY, get_check, rows_to_csv_response


def _require_superuser(request):
    """Raise PermissionDenied unless the logged-in admin is a superuser."""
    if not request.user.is_superuser:
        raise PermissionDenied("Data Health pages require superuser access.")


def _admin_context(request, title):
    """Base admin chrome context (site header, nav, etc.) plus a page title."""
    context = admin.site.each_context(request)
    context['title'] = title
    return context


def dashboard(request):
    """Hub page: list every registered check with its flagged-row count."""
    _require_superuser(request)
    checks = [
        {
            'slug': c.slug,
            'title': c.title,
            'description': c.description,
            'group': c.group,
            'count': c.count(),
        }
        for c in REGISTRY
    ]
    context = _admin_context(request, title='Data Health')
    context['checks'] = checks
    return render(request, 'admin/data_health/dashboard.html', context)


def detail(request, check_slug):
    """Detail page: full table for one check plus a CSV-download link."""
    _require_superuser(request)
    check = get_check(check_slug)
    if check is None:
        raise Http404("Unknown data-health check.")
    # Flatten dict rows into cell lists aligned to the column order so the
    # template can render them without a dynamic dict-lookup filter.
    columns = check.columns
    rows = [[row.get(col, '') for col in columns] for row in check.get_rows()]
    context = _admin_context(request, title=check.title)
    context['check'] = check
    context['columns'] = columns
    context['rows'] = rows
    return render(request, 'admin/data_health/detail.html', context)


def export_csv(request, check_slug):
    """Stream one check's rows as a CSV download (generated on the fly)."""
    _require_superuser(request)
    check = get_check(check_slug)
    if check is None:
        raise Http404("Unknown data-health check.")
    return rows_to_csv_response(check)
