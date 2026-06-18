"""
Helpers for building per-page SEO / social-sharing metadata.

These are used by views to populate the optional ``page_meta`` context dict
consumed by ``base.html`` (meta description, Open Graph, Twitter Card, and
canonical tags). Keeping the truncation/stripping logic here means each view
sets a clean string once and the template stays presentation-only.

See ``website/templates/website/base.html`` for how ``page_meta`` is rendered.
"""

import json

from django.conf import settings
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe
from django.utils.text import Truncator

# Recommended upper bound for a meta description; Google typically renders
# ~150-160 chars in a snippet. og:description can run longer but we keep one
# value for both for simplicity and consistency.
META_DESCRIPTION_MAX_CHARS = 160


def meta_description(html, max_chars=META_DESCRIPTION_MAX_CHARS):
    """
    Turn (possibly HTML) body text into a clean, length-bounded meta description.

    Strips tags, collapses surrounding whitespace, and truncates on a word
    boundary with an ellipsis. Returns ``None`` for empty/whitespace-only input
    so callers can fall back to a page-type default (``base.html`` substitutes
    the lab-wide description when ``page_meta.description`` is falsy).

    Example:
        >>> meta_description("<p>Hello   <b>world</b></p>")
        'Hello world'
    """
    if not html:
        return None
    text = " ".join(strip_tags(html).split())
    if not text:
        return None
    return Truncator(text).chars(max_chars)


def site_scheme(request):
    """
    The canonical scheme for absolute URLs built in views (https on the servers,
    request.scheme in local dev). Mirrors the ``site_scheme`` context processor
    (website/context_processors.py) so view-built JSON-LD URLs match the
    template-built canonical/OG URLs. See #1236.
    """
    return request.scheme if settings.DEBUG else 'https'


def absolute_url(request, path):
    """Build an absolute, scheme-correct URL from a root-relative path."""
    if not path:
        return None
    return f"{site_scheme(request)}://{request.get_host()}{path}"


def render_jsonld(data):
    """
    Serialize a dict (or list of dicts) to a JSON string safe to embed inside a
    ``<script type="application/ld+json">`` tag.

    json.dumps does not escape ``<``/``>``/``&``, so a value containing the
    literal ``</script>`` (e.g. in a bio) could otherwise break out of the
    script element. We escape those three characters as ``\\uXXXX`` — still valid
    JSON, but inert in HTML — then mark the result safe so the template emits it
    verbatim. Returns ``None`` for falsy input so callers/templates can skip the
    tag entirely.
    """
    if not data:
        return None
    json_str = json.dumps(data, ensure_ascii=False)
    json_str = (json_str.replace('<', '\\u003c')
                        .replace('>', '\\u003e')
                        .replace('&', '\\u0026'))
    return mark_safe(json_str)
