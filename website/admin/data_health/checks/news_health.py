"""
Data-health check: News items missing a slug or an author.

A blank/null ``slug`` breaks the canonical ``/news/<slug>/`` URL (the
``generate_slugs_for_old_news_items`` command backfills these), and a null
``author`` leaves the item unattributed. Read-only.
"""

from django.db.models import Q

from website.admin.data_health.registry import HealthCheck, register_check
from website.models import News


@register_check
class NewsHealthCheck(HealthCheck):
    slug = 'news-health'
    title = 'News health'
    description = "News items missing a slug or an author."
    group = 'People'
    columns = ['id', 'title', 'date', 'missing_slug', 'has_author']

    def get_rows(self):
        flagged = News.objects.filter(
            Q(slug__isnull=True) | Q(slug='') | Q(author__isnull=True)
        ).order_by('-date')

        rows = []
        for item in flagged:
            rows.append({
                'id': item.pk,
                'title': item.title,
                'date': item.date.isoformat() if item.date else '',
                'missing_slug': not bool(item.slug),
                'has_author': item.author_id is not None,
            })
        return rows
