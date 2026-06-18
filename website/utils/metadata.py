"""
Helpers for building per-page SEO / social-sharing metadata.

These are used by views to populate the optional ``page_meta`` context dict
consumed by ``base.html`` (meta description, Open Graph, Twitter Card, and
canonical tags). Keeping the truncation/stripping logic here means each view
sets a clean string once and the template stays presentation-only.

See ``website/templates/website/base.html`` for how ``page_meta`` is rendered.
"""

from django.utils.html import strip_tags
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
