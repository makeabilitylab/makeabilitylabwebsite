"""
Custom error pages (#1190).

Django routes unmatched URLs and unhandled server errors to the module-level
``handler404`` / ``handler500`` callables declared in the *root* URLconf
(``makeabilitylab/urls.py``) -- not the app URLconf. These views render the
branded Makeability Lab error templates instead of Django's bare defaults.

Important: custom handlers only run when ``DEBUG=False``. In local dev
(``DEBUG=True``) Django shows its own debug traceback page instead, so to *see*
these pages while iterating use the DEBUG-only preview routes wired up in
``website/urls.py`` (``/404-preview/``, ``/500-preview/``).
"""

import logging

from django.shortcuts import render

# Module logger (configured in settings.LOGGING).
_logger = logging.getLogger(__name__)


def _render_404(request, status=404):
    """Render the 404 template. Shared by the handler and the dev preview."""
    context = {
        # Echoed back to the visitor so they can spot a typo'd URL. Rendered
        # through Django's autoescaping in the template (never {% autoescape off %})
        # so a crafted path can't inject markup -- a regression test pins this.
        "requested_path": request.path,
        # base.html keys the navbar to a readable light theme when this is set,
        # which the dark 404 canvas needs.
        "navbar_white": True,
    }
    return render(request, "website/404.html", context, status=status)


def custom_404(request, exception):
    """
    handler404. Logs the missing path (useful for spotting broken inbound links)
    and renders the branded 404 page with a 404 status.

    ``exception`` is supplied by Django (the raised ``Http404``); we don't echo
    it to the page -- it can contain internal detail -- but it's available for
    logging if needed.
    """
    _logger.warning("404 (page not found) for path: %s", request.path)
    return _render_404(request)


def custom_500(request):
    """
    handler500. Note Django calls this with *only* ``request`` (no exception),
    and renders it with the bare ``django.template.context.RequestContext`` --
    so the template must not depend on custom context processors. ``500.html``
    is intentionally a static, no-JS fallback for that reason.
    """
    _logger.error("500 (server error) for path: %s", request.path)
    return render(request, "website/500.html", status=500)


def preview_404(request):
    """DEBUG-only: view the 404 page at a real URL with static files served."""
    return _render_404(request, status=200)


def preview_500(request):
    """DEBUG-only: view the 500 page at a real URL with static files served."""
    return render(request, "website/500.html", {"navbar_white": True}, status=200)
