"""
Data-health check: clusters of Person records that share a normalized name.

These are the candidates for the issue #1275 dedup work — either *true
duplicates* (one human, multiple rows) to merge, or genuine *namesakes* to
keep separate. One row is emitted per person in any multi-person name
cluster, with relation counts to support the merge / keep / delete decision
(``total_refs == 0`` means a safe-to-delete shell). Strictly read-only.
"""

from collections import defaultdict

from website.admin.data_health.registry import HealthCheck, register_check
from website.models import Person, Position
from website.utils.name_utils import normalize_person_name, is_default_person_image


def _reverse_count(person, attr):
    """Count related objects via a reverse manager, or 0 if it doesn't exist."""
    manager = getattr(person, attr, None)
    return manager.count() if manager is not None else 0


@register_check
class DuplicatePeopleCheck(HealthCheck):
    slug = 'duplicate-people'
    title = 'Duplicate people (same normalized name)'
    description = (
        'Person records that share an accent-folded name key — candidates for '
        'merge or namesake review (issue #1275). total_refs == 0 is a safe-to-'
        'delete shell.'
    )
    group = 'People'
    columns = [
        'cluster_key', 'id', 'first_name', 'middle_name', 'last_name',
        'url_name', 'email', 'personal_website', 'github', 'linkedin',
        'pub_count', 'talk_count', 'poster_count', 'video_count',
        'position_count', 'projectrole_count', 'news_authored_count',
        'advisor_count', 'co_advisor_count', 'grad_mentor_count',
        'total_refs', 'has_real_image',
        'earliest_position_date', 'latest_position_date',
    ]

    def get_rows(self):
        # Group all people by their normalized name key.
        clusters = defaultdict(list)
        for p in Person.objects.all().prefetch_related('position_set'):
            clusters[normalize_person_name(p.first_name, p.last_name)].append(p)

        rows = []
        for key, members in clusters.items():
            if len(members) < 2:
                continue  # only multi-person clusters are dups / namesakes
            for p in members:
                rows.append(self._row(key, p))

        # Stable, scannable ordering: by cluster key then id.
        rows.sort(key=lambda r: (r['cluster_key'], r['id']))
        return rows

    def _row(self, key, p):
        positions = list(p.position_set.all())  # prefetched; no extra query

        pub_count = _reverse_count(p, 'publication_set')
        talk_count = _reverse_count(p, 'talk_set')
        poster_count = _reverse_count(p, 'poster_set')
        # Video has no authors relation today, so this is always 0 — kept for
        # parity with the #1275 export spec and future-proofing.
        video_count = _reverse_count(p, 'video_set')
        position_count = len(positions)
        projectrole_count = _reverse_count(p, 'projectrole_set')
        news_count = _reverse_count(p, 'authored_news')
        # Advisor self-references are easy to miss on merge — count them.
        advisor_count = Position.objects.filter(advisor=p).count()
        co_advisor_count = Position.objects.filter(co_advisor=p).count()
        grad_mentor_count = Position.objects.filter(grad_mentor=p).count()

        total_refs = (pub_count + talk_count + poster_count + video_count
                      + position_count + projectrole_count + news_count
                      + advisor_count + co_advisor_count + grad_mentor_count)

        start_dates = [pos.start_date for pos in positions if pos.start_date]
        end_dates = [pos.end_date for pos in positions if pos.end_date]

        return {
            'cluster_key': key,
            'id': p.pk,
            'first_name': p.first_name,
            'middle_name': p.middle_name or '',
            'last_name': p.last_name,
            'url_name': p.url_name,
            'email': p.email or '',
            'personal_website': p.personal_website or '',
            'github': p.github or '',
            'linkedin': p.linkedin or '',
            'pub_count': pub_count,
            'talk_count': talk_count,
            'poster_count': poster_count,
            'video_count': video_count,
            'position_count': position_count,
            'projectrole_count': projectrole_count,
            'news_authored_count': news_count,
            'advisor_count': advisor_count,
            'co_advisor_count': co_advisor_count,
            'grad_mentor_count': grad_mentor_count,
            'total_refs': total_refs,
            # Best-effort (see is_default_person_image caveat for headshots).
            'has_real_image': not is_default_person_image(p.image),
            'earliest_position_date': min(start_dates).isoformat() if start_dates else '',
            'latest_position_date': max(end_dates).isoformat() if end_dates else '',
        }
