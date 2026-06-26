"""
Data-health check: poster publications with no linked poster artifact.

A Poster-type publication should point at its ``Poster`` (the actual poster
PDF/image); without that link the poster isn't shown on the site. The fix is to
add (or link) the poster from the publication's edit page. Shared scoping and
row shape live in :mod:`._companion_base`. Read-only.
"""

from website.admin.data_health.checks._companion_base import CompanionArtifactCheck
from website.admin.data_health.registry import register_check
from website.models.publication import PubType


@register_check
class PosterPapersWithoutPosterCheck(CompanionArtifactCheck):
    slug = 'poster-papers-without-poster'
    title = 'Poster papers without a linked poster'
    description = (
        'Publications of type Poster with no linked Poster artifact — the '
        "poster won't appear on the site. Add or link it from the "
        "publication's edit page. Pre-Makeability-Lab and not-yet-presented "
        '(future-dated) papers are excluded.'
    )
    venue_type = PubType.POSTER
    companion_field = 'poster'
    require_full_paper = False
