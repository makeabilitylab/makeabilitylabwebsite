"""
Propagate a publication's projects onto its own talk / video / poster (#649).

A ``Publication``'s child artifacts -- the ``talk`` that presented it, the
teaser ``video``, the ``poster`` -- are the *same* scholarly artifact, so they
belong to the same projects as the publication. This one-shot command copies a
publication's ``projects`` onto any of its children that currently have **none**,
which clears the "parent publication is linked -- inherit its projects" rows the
``UnlinkedArtifactsCheck`` data-health check flags.

Safety properties:

- **Additive only.** Never removes a link and never touches a child that already
  has one or more projects (so an intentional, different linkage is preserved).
- **Idempotent.** Re-running changes nothing once children are populated, which
  is why it is safe to run on every container start from ``docker-entrypoint.sh``
  (it self-heals future papers whose children are added without a project).

Run manually with ``--dry-run`` to preview without writing.
"""

import logging

from django.core.management.base import BaseCommand

from website.models import Publication

_logger = logging.getLogger(__name__)

# Publication FK fields pointing at its child artifacts (all nullable).
CHILD_FIELDS = ('talk', 'video', 'poster')


class Command(BaseCommand):
    help = ("Copy each publication's projects onto its own talk/video/poster "
            "children that currently have no project (#649). Additive and "
            "idempotent.")

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="Report what would change without writing to the database.",
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        prefix = '[dry-run] ' if dry_run else ''
        _logger.info("%sRunning propagate_publication_projects (#649)...", prefix)

        children_updated = 0
        pubs = (Publication.objects
                .prefetch_related('projects', 'talk__projects',
                                  'video__projects', 'poster__projects'))
        for pub in pubs:
            parent_projects = list(pub.projects.all())
            if not parent_projects:
                continue  # nothing to propagate

            for field in CHILD_FIELDS:
                child = getattr(pub, field, None)
                if child is None:
                    continue
                if child.projects.exists():
                    continue  # already linked -- leave it alone

                _logger.info(
                    "%sLinking %s id=%s ('%s') to projects %s (from publication "
                    "id=%s)",
                    prefix, field, child.pk, child.title,
                    [p.pk for p in parent_projects], pub.pk,
                )
                if not dry_run:
                    child.projects.add(*parent_projects)
                children_updated += 1

        _logger.info("%sLinked %d child artifact(s) to their publication's "
                     "projects.", prefix, children_updated)
        self.stdout.write(
            f"{prefix}Linked {children_updated} child artifact(s) "
            f"to their publication's projects."
        )
