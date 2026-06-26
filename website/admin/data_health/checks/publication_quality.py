"""
Data-health check: Publication metadata completeness + duplicate titles.

Publications are the central artifact, so missing core metadata (PDF, date,
venue, thumbnail) degrades the public site and citations. Also flags
publications that share a normalized title (possible duplicate entry).
Read-only.
"""

from collections import defaultdict

from website.admin.data_health.registry import HealthCheck, register_check
from website.models import Publication


def _normalize_title(title):
    """Lowercased, alphanumeric-only title key for duplicate detection."""
    return ''.join(ch for ch in (title or '').lower() if ch.isalnum())


@register_check
class PublicationQualityCheck(HealthCheck):
    slug = 'publication-quality'
    title = 'Publication data quality'
    description = (
        'Publications missing a PDF, date, venue (forum_name), or thumbnail, '
        'and publications that share a normalized title (possible duplicates).'
    )
    group = 'Artifacts'
    link_model = 'publication'
    columns = ['id', 'title', 'date', 'missing_fields', 'dup_title']

    def get_rows(self):
        pubs = list(Publication.objects.all())

        # Find normalized titles shared by more than one publication.
        title_counts = defaultdict(int)
        for pub in pubs:
            key = _normalize_title(pub.title)
            if key:
                title_counts[key] += 1

        rows = []
        for pub in pubs:
            missing = []
            if not pub.pdf_file:
                missing.append('pdf_file')
            if not pub.date:
                missing.append('date')
            if not pub.forum_name:
                missing.append('forum_name')
            if not pub.thumbnail:
                missing.append('thumbnail')

            key = _normalize_title(pub.title)
            dup_title = bool(key) and title_counts[key] > 1

            if not missing and not dup_title:
                continue  # this publication is healthy

            rows.append({
                'id': pub.pk,
                'title': pub.title or '',
                'date': pub.date.isoformat() if pub.date else '',
                'missing_fields': ', '.join(missing),
                'dup_title': dup_title,
            })

        rows.sort(key=lambda r: (not r['dup_title'], r['title']))
        return rows
