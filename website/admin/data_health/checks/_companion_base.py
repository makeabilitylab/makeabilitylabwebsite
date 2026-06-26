"""
Shared base for "publication is missing an expected companion artifact" checks.

Some publication types almost always ship with a companion artifact:

- a full **conference paper** is presented with a **talk**, and
- a **poster** publication points at its **poster** artifact.

Each gap is surfaced as its own dashboard check (the corrective action differs)
but the scoping and row shape are identical, so they share this base. A
subclass only sets the venue type to match, the companion FK that should be
populated, and (optionally) whether to restrict to full papers.

Scoping mirrors the unlinked-artifacts check to avoid permanent false
positives:

- **Pre-Makeability-Lab work is excluded** (date before
  ``settings.DATE_MAKEABILITYLAB_FORMED``) — grad-school-era papers predate the
  lab's talk/poster records.
- **Not-yet-presented papers are excluded** (``to_appear()`` — a future date);
  the companion usually isn't recorded until the work is presented.

Read-only: never calls ``.save()`` or mutates the DB.
"""

from django.conf import settings

from website.admin.data_health.registry import HealthCheck
from website.models import Publication


class CompanionArtifactCheck(HealthCheck):
    """Base check: publications of one venue type missing a companion FK.

    Subclasses set :attr:`venue_type`, :attr:`companion_field`, and optionally
    :attr:`require_full_paper`; everything else (columns, scoping, the link to
    the publication's edit page) is shared.
    """

    group = 'Artifacts'
    link_model = 'publication'  # each row's fix happens on the publication form
    columns = ['id', 'title', 'date', 'forum_name', 'first_author']

    #: ``PubType`` value this check applies to (e.g. ``PubType.CONFERENCE``).
    venue_type = None
    #: Publication FK that should be populated (e.g. ``'talk'`` / ``'poster'``).
    companion_field = None
    #: When True, skip extended abstracts (short-form papers rarely have one).
    require_full_paper = False

    def get_rows(self):
        qs = (Publication.objects
              .filter(pub_venue_type=self.venue_type)
              .prefetch_related('authors'))

        rows = []
        for pub in qs:
            if getattr(pub, f'{self.companion_field}_id'):
                continue  # companion already linked — healthy
            if self.require_full_paper and pub.is_extended_abstract():
                continue  # short-form paper; a talk isn't expected
            if pub.to_appear():
                continue  # not presented yet — companion expected later
            if pub.date and pub.date < settings.DATE_MAKEABILITYLAB_FORMED:
                continue  # pre-Makeability-Lab; not expected to have one

            person = pub.get_person()
            rows.append({
                'id': pub.pk,
                'title': pub.title or '',
                'date': pub.date.isoformat() if pub.date else '',
                'forum_name': pub.forum_name or '',
                'first_author': person.get_full_name() if person else '',
            })

        # Newest first (stable two-pass sort: by title, then by date desc).
        rows.sort(key=lambda r: r['title'])
        rows.sort(key=lambda r: r['date'], reverse=True)
        return rows
