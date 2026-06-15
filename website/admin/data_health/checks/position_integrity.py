"""
Data-health check: Position records and the advisor/mentor graph.

Surfaces people with no Position at all, positions whose dates are inverted
(``start_date > end_date``), and self-referential advisor links
(``advisor`` / ``co_advisor`` / ``grad_mentor`` pointing at the position's own
person). The advisor self-refs overlap the issue #1275 merge surface, so this
doubles as a pre-merge sanity check. Read-only.
"""

from website.admin.data_health.registry import HealthCheck, register_check
from website.models import Person, Position


@register_check
class PositionIntegrityCheck(HealthCheck):
    slug = 'position-integrity'
    title = 'Position & advisor-graph integrity'
    description = (
        'People with no position, positions with start_date after end_date, '
        'and advisor/co_advisor/grad_mentor links that point at the person '
        'themselves.'
    )
    group = 'People'
    columns = ['person_id', 'name', 'issue', 'detail']

    def get_rows(self):
        rows = []

        # People with no Position at all.
        for person in Person.objects.filter(position__isnull=True):
            rows.append({
                'person_id': person.pk,
                'name': person.get_full_name(),
                'issue': 'no position',
                'detail': '',
            })

        # Per-position anomalies.
        positions = Position.objects.select_related(
            'person', 'advisor', 'co_advisor', 'grad_mentor')
        for pos in positions:
            person = pos.person
            if pos.start_date and pos.end_date and pos.start_date > pos.end_date:
                rows.append({
                    'person_id': person.pk,
                    'name': person.get_full_name(),
                    'issue': 'inverted dates',
                    'detail': f'start {pos.start_date} > end {pos.end_date} (position {pos.pk})',
                })
            for field in ('advisor', 'co_advisor', 'grad_mentor'):
                related = getattr(pos, field)
                if related is not None and related.pk == person.pk:
                    rows.append({
                        'person_id': person.pk,
                        'name': person.get_full_name(),
                        'issue': f'self-{field}',
                        'detail': f'position {pos.pk} lists the person as their own {field}',
                    })

        rows.sort(key=lambda r: (r['name'].lower(), r['issue']))
        return rows
