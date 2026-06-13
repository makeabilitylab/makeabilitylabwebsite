from django.http import HttpResponse, Http404
from django.shortcuts import redirect
from website.models import Publication
import os
import logging
import website.utils.ml_utils as ml_utils

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)


def serve_pdf(request, filename):
    """
    Serve a Publication PDF by URL filename.

    Tries an exact match first (by ``pdf_file`` path ending in the
    requested name); if no exact match, falls back to a fuzzy ``difflib``
    match and redirects. The fuzzy fallback preserves link integrity for
    stale external links to papers whose filenames have since changed.

    Note on production routing (as of 2026-06-13):
    Apache on production serves ``/media/publications/*`` directly as
    static files and never falls through to Django, so this view is
    currently only reached on the test server (Django runserver) and in
    local dev. If CSE IT updates Apache to fall through on 404, the
    fuzzy-match feature lights up in production too.
    """
    _logger.debug(f"serve_pdf with filename={filename}")

    # Exact match. ``.filter(...).first()`` returns None on miss and a
    # single Publication on hit; it can't raise MultipleObjectsReturned
    # (unlike ``.get()``), so the previous 500-on-duplicate-substring
    # bug is gone. ``__iendswith`` (not ``__icontains``) confines matches
    # to paths ending with the requested name, killing the substring-
    # probe enumeration vector (".pdf" no longer matches every pub).
    artifact = (Publication.objects
                .filter(pdf_file__iendswith=filename)
                .first())

    if artifact is not None:
        _logger.debug(f"Exact match for {filename}")
        response = HttpResponse(artifact.pdf_file.read(),
                                content_type='application/pdf')
        basename = os.path.basename(artifact.pdf_file.name)
        response['Content-Disposition'] = f'inline;filename={basename}'
        return response

    # No exact match — try fuzzy fallback for stale external links.
    _logger.debug(f"{filename} not found exactly; trying fuzzy match")
    closest = get_closest_filename_from_database(filename, 0.7)
    if closest:
        closest_basename = os.path.basename(closest)
        _logger.debug(f"Redirecting to /media/publications/{closest_basename}")
        return redirect(f'/media/publications/{closest_basename}')

    raise Http404(f"The PDF {filename} was not found.")


def get_closest_filename_from_database(query_filename, cutoff=0.8):
    """
    Return the closest matching ``pdf_file`` path in the Publication
    table via ``difflib``, or None if nothing matches above the cutoff.
    """
    all_filenames = Publication.objects.values_list('pdf_file', flat=True)
    return ml_utils.get_closest_match(query_filename, all_filenames, cutoff)
