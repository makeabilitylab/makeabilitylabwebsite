"""
Data-health check: artifacts not linked to any project (issue #649).

As the lab keeps adding projects, older talks / papers / videos / posters need
to be linked back to the projects they belong to (the ``projects`` M2M). This
check surfaces every artifact that currently has **zero** projects so the
backlog stays visible instead of living in a one-off issue.

Scoping decisions:

- **Pre-Makeability-Lab work is excluded.** Artifacts dated before
  ``settings.DATE_MAKEABILITYLAB_FORMED`` (the grad-school era; same cutoff the
  publications view uses) don't belong to a lab project and would be permanent
  false positives, so they're filtered out. Artifacts with **no date** are kept
  — a missing date is itself worth a look.
- **Propagation hint.** A ``Talk`` / ``Video`` / ``Poster`` that is the child of
  a publication (via ``Publication.talk_id`` / ``video_id`` / ``poster_id``)
  should inherit that publication's projects. When the parent publication is
  already linked, the row's ``note`` says so — those are the quickest wins.

Read-only: never calls ``.save()`` or mutates the DB.
"""

from django.conf import settings
from django.urls import reverse

from website.admin.data_health.registry import HealthCheck, register_check
from website.models import Poster, Publication, Talk, Video


@register_check
class UnlinkedArtifactsCheck(HealthCheck):
    slug = 'unlinked-artifacts'
    title = 'Artifacts not linked to a project'
    description = (
        'Talks, papers, videos, and posters with no project assigned (#649). '
        'Pre-Makeability-Lab work (before the lab was formed) is excluded. '
        'Rows whose parent publication is already linked can simply inherit '
        'its projects.'
    )
    group = 'Artifacts'
    columns = ['type', 'id', 'title', 'date', 'first_author', 'note']

    def get_rows(self):
        rows = []
        rows += self._artifact_rows(Publication, 'Publication')
        rows += self._artifact_rows(Talk, 'Talk', parent_fk='talk')
        rows += self._artifact_rows(Poster, 'Poster', parent_fk='poster')
        rows += self._artifact_rows(Video, 'Video', parent_fk='video')

        # Newest first within type; types stay grouped by insertion order above.
        rows.sort(key=lambda r: (r['type'], r['date'] or '', r['id']),
                  reverse=True)
        rows.sort(key=lambda r: r['type'])
        return rows

    def _artifact_rows(self, model, type_label, parent_fk=None):
        """Build rows for one artifact ``model`` with no linked projects.

        ``parent_fk`` is the ``Publication`` FK name pointing at this child
        (``'talk'`` / ``'video'`` / ``'poster'``); when set, we note whether the
        parent publication is already linked so its projects can be inherited.
        """
        qs = (model.objects
              .filter(projects__isnull=True)
              .prefetch_related('projects'))

        # Map child id -> whether its parent publication has projects.
        parent_linked = {}
        if parent_fk:
            pub_qs = (Publication.objects
                      .filter(**{f'{parent_fk}__isnull': False})
                      .values_list(f'{parent_fk}_id', 'projects'))
            for child_id, project_id in pub_qs:
                # project_id is None when the parent pub itself has no projects.
                parent_linked[child_id] = parent_linked.get(child_id, False) or \
                    project_id is not None

        rows = []
        for obj in qs:
            artifact_date = getattr(obj, 'date', None)
            if artifact_date and artifact_date < settings.DATE_MAKEABILITYLAB_FORMED:
                continue  # pre-Makeability-Lab; not expected to have a project

            note = ''
            if parent_fk and parent_linked.get(obj.pk):
                note = 'parent publication is linked — inherit its projects'

            rows.append({
                'type': type_label,
                'id': obj.pk,
                'title': obj.title,
                'date': artifact_date.isoformat() if artifact_date else '',
                'first_author': self._first_author(obj),
                'note': note,
            })
        return rows

    @staticmethod
    def _first_author(obj):
        """First-author last name (Videos have no authors → '')."""
        getter = getattr(obj, 'get_first_author_last_name', None)
        return getter() if getter else ''

    def row_link(self, row):
        """Deep-link each row to its artifact edit page so the editor can add
        the project right there."""
        model_name = row['type'].lower()
        url = reverse(f'admin:website_{model_name}_change', args=[row['id']])
        return ('Open →', url)
