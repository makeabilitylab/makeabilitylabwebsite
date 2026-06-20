"""
Data-health check: keywords that collapse to the same normalized text.

Keywords are free-text with no uniqueness constraint, so case/whitespace
variants coexist (e.g. ``Speech`` / ``speech`` / ``Speech ``) and fragment the
public keyword pages. This check *finds* those near-duplicate clusters; the
``Merge selected keywords`` action on the Keyword admin changelist (#1352) is
the tool to *fix* them. Strictly read-only.

One row is emitted per keyword in any cluster of two or more keywords that
share a normalized key (``.strip().casefold()``), with per-model usage counts
to support the merge decision (which variant to keep as the target).
"""

from collections import defaultdict

from website.admin.data_health.registry import HealthCheck, register_check
from website.models import (Keyword, Publication, Talk, Poster, Grant,
                            Project, ProjectUmbrella)

# Reverse accessor on Keyword for each model that holds a `keywords` M2M.
# (Video is not an Artifact, so it has no keywords.) Keep this in lockstep with
# KEYWORD_USERS in website/admin/keyword_admin.py.
KEYWORD_REVERSE_ACCESSORS = (
    ('publication_count', 'publication_set'),
    ('talk_count', 'talk_set'),
    ('poster_count', 'poster_set'),
    ('grant_count', 'grant_set'),
    ('project_count', 'project_set'),
    ('project_umbrella_count', 'projectumbrella_set'),
)


def normalize_keyword(text):
    """Cluster key for near-duplicate detection: trim + case-fold.

    casefold() is the aggressive, Unicode-aware lower() — so ``Speech``,
    ``speech``, and ``Speech `` all collapse to the same key.
    """
    return (text or '').strip().casefold()


@register_check
class DuplicateKeywordsCheck(HealthCheck):
    slug = 'duplicate-keywords'
    title = 'Duplicate keywords (same normalized text)'
    description = (
        'Keywords that collapse to the same text after trimming whitespace and '
        'folding case (e.g. "Speech" / "speech" / "Speech ") — candidates for '
        'the "Merge selected keywords" action on the Keyword admin (#1352).'
    )
    group = 'Artifacts'
    columns = [
        'cluster_key', 'id', 'keyword',
        'publication_count', 'talk_count', 'poster_count', 'grant_count',
        'project_count', 'project_umbrella_count', 'total_uses',
    ]

    def get_rows(self):
        # Group every keyword by its normalized key.
        clusters = defaultdict(list)
        for kw in Keyword.objects.all():
            clusters[normalize_keyword(kw.keyword)].append(kw)

        rows = []
        for key, members in clusters.items():
            if len(members) < 2:
                continue  # only multi-keyword clusters are near-duplicates
            for kw in members:
                rows.append(self._row(key, kw))

        # Stable, scannable ordering: cluster together, then by id.
        rows.sort(key=lambda r: (r['cluster_key'], r['id']))
        return rows

    def _row(self, key, kw):
        counts = {col: getattr(kw, accessor).count()
                  for col, accessor in KEYWORD_REVERSE_ACCESSORS}
        return {
            'cluster_key': key,
            'id': kw.pk,
            'keyword': kw.keyword,
            **counts,
            'total_uses': sum(counts.values()),
        }
