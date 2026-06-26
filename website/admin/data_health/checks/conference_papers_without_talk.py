"""
Data-health check: full conference papers with no linked talk.

A Conference-type publication is normally presented with a talk, so a full
conference paper whose ``talk`` FK is empty is usually a data-entry gap. The fix
is to add (or link) the talk from the publication's edit page. Extended
abstracts are excluded — short-form conference items often have no talk. Shared
scoping and row shape live in :mod:`._companion_base`. Read-only.
"""

from website.admin.data_health.checks._companion_base import CompanionArtifactCheck
from website.admin.data_health.registry import register_check
from website.models.publication import PubType


@register_check
class ConferencePapersWithoutTalkCheck(CompanionArtifactCheck):
    slug = 'conference-papers-without-talk'
    title = 'Conference papers without a talk'
    description = (
        'Full conference papers (Conference venue type, not an extended '
        'abstract) with no linked talk. Most should have one — add or link the '
        "talk from the publication's edit page. Pre-Makeability-Lab and "
        'not-yet-presented (future-dated) papers are excluded.'
    )
    venue_type = PubType.CONFERENCE
    companion_field = 'talk'
    require_full_paper = True
