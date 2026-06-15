"""
Data-health check: Person.url_name collisions and unresolved placeholders.

Two members sharing a ``url_name`` cause ``MultipleObjectsReturned`` ->
HTTP 500 on ``/member/<url_name>/`` (issue #1206). Rows still holding the
model default ``'placeholder'`` were created/never re-saved before the
collision loop landed. Strictly read-only.
"""

from collections import defaultdict

from website.admin.data_health.registry import HealthCheck, register_check
from website.models import Person


@register_check
class UrlNameCollisionsCheck(HealthCheck):
    slug = 'url-name-collisions'
    title = 'url_name collisions & placeholders'
    description = (
        "Person rows sharing a url_name (the live /member/ 500 source, issue "
        "#1206) or still set to the default 'placeholder'."
    )
    group = 'People'
    columns = ['url_name', 'count', 'person_ids', 'names']

    def get_rows(self):
        by_url_name = defaultdict(list)
        for p in Person.objects.all():
            by_url_name[p.url_name].append(p)

        rows = []
        for url_name, people in by_url_name.items():
            is_collision = len(people) > 1
            is_placeholder = url_name == 'placeholder'
            if not (is_collision or is_placeholder):
                continue
            rows.append({
                'url_name': url_name,
                'count': len(people),
                'person_ids': ', '.join(str(p.pk) for p in sorted(people, key=lambda x: x.pk)),
                'names': '; '.join(p.get_full_name() for p in people),
            })

        # Worst offenders first, then alphabetical.
        rows.sort(key=lambda r: (-r['count'], r['url_name']))
        return rows
