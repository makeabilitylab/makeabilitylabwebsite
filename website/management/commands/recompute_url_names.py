"""
Recompute every Person.url_name so historical collisions de-collide (#1206).

Person.url_name is derived in Person.save(), but the collision-resolution loop
only protects rows saved *after* it landed. Rows imported/created earlier and
never re-saved can still share a bare url_name, which causes
MultipleObjectsReturned -> HTTP 500 on /member/<url_name>/. This command
re-derives a unique url_name for every person using the same shared logic
(website.utils.name_utils.build_unique_url_name), giving namesakes stable,
readable URLs (a middle-initial differentiator where possible, else a numeric
suffix).

People are processed in ascending pk order, so within a same-name cluster the
earliest record keeps the bare url_name (e.g. ``jasminezhang``) and later ones
get differentiated (``jasminexzhang`` / ``jasminezhang2``). Assignment is
deterministic, so the command is idempotent — re-running changes nothing.

Writes use ``.update()`` to set only the url_name column, deliberately bypassing
Person.save() (no Star Wars image fallback, no bio_datetime_modified churn).
Runs on every container start (docker-entrypoint.sh) and is safe to re-run.

Usage:
    python manage.py recompute_url_names            # apply
    python manage.py recompute_url_names --dry-run  # preview changes only
"""

import logging

from django.core.management.base import BaseCommand

from website.models import Person
from website.utils.name_utils import build_unique_url_name

_logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Re-derive a unique url_name for every Person (de-collides historical duplicates, #1206)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Report what would change without writing anything.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        assigned = set()
        changes = []  # (pk, old, new) for rows whose url_name actually changes

        # Ascending pk = creation order, so the earliest row in a name cluster
        # keeps the bare url_name and later namesakes get differentiated.
        for person in Person.objects.order_by('pk').only(
                'pk', 'first_name', 'middle_name', 'last_name', 'url_name'):
            new_url_name = build_unique_url_name(
                person.first_name, person.middle_name, person.last_name,
                is_taken=assigned.__contains__,
            )
            assigned.add(new_url_name)
            if new_url_name != person.url_name:
                changes.append((person.pk, person.url_name, new_url_name))

        for pk, old, new in changes:
            _logger.debug("recompute_url_names: %s -> %s (pk=%s)", old, new, pk)
            self.stdout.write(f"  {old or '(blank)'} -> {new}  (pk={pk})")
            if not dry_run:
                Person.objects.filter(pk=pk).update(url_name=new)

        verb = 'would change' if dry_run else 'changed'
        summary = f"recompute_url_names: {verb} {len(changes)} url_name(s)."
        self.stdout.write(self.style.SUCCESS(summary))
        if not dry_run:
            _logger.info(summary)
