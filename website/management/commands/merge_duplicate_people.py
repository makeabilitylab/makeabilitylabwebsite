"""
Merge duplicate ``Person`` records, driven by a reviewed decisions file.

Part of the issue #1275 dedup work. Over ~15 years the database accumulated
duplicate ``Person`` rows (one human, several rows from un-deduped imports).
This command consolidates each cluster into one canonical record, relocating
**every** related object (publications, talks, posters, grants, awards,
positions, project roles, news, and the advisor/co-advisor/grad-mentor
self-references) before deleting the now-empty duplicate.

Why a management command (not a data migration): migrations are gitignored and
regenerated per-environment here, so the established pattern is a one-shot
command verified via the logs (see ``generate_slugs_for_old_news_items`` etc.).

Safety model:
  * **Dry-run by default.** Without ``--apply`` it prints the plan and changes
    nothing. Pass ``--apply`` to actually mutate.
  * **Idempotent.** A ``merge`` whose source row is already gone is a no-op, so
    re-running an applied decisions file is safe.
  * **Atomic per row.** Each merge runs in ``transaction.atomic()``.
  * **Generic relation walk.** Relations are discovered via
    ``Person._meta.get_fields()`` rather than hardcoded, so a new FK/M2M to
    Person can't silently orphan data.

Decisions file: CSV with columns ``source_id, action, target_id, note``.
  * ``merge``  — relocate everything from ``source_id`` onto ``target_id``, then
                 delete ``source_id``.
  * ``delete`` — delete ``source_id`` (refused unless it has zero references).
  * ``keep``   — no-op; documents a reviewed namesake to leave alone.
Ids only (no emails) so the reviewed file is safe to commit to the public repo;
member names are already public.

Usage:
    python manage.py merge_duplicate_people --decisions dedup_decisions.csv
    python manage.py merge_duplicate_people --decisions dedup_decisions.csv --apply
"""

import csv
import logging

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from website.models import Person

_logger = logging.getLogger(__name__)

# Scalar (non-relational) fields whose *blank* value on the target is backfilled
# from the source during a merge. We never overwrite a populated target field,
# and we deliberately leave the image/cropping fields and the derived url_name /
# bio_datetime_modified alone (the target is the chosen canonical record; its
# headshot stays put — see module docstring / issue #1275).
SCALAR_BACKFILL_FIELDS = [
    'email', 'personal_website', 'github', 'twitter', 'linkedin',
    'mastodon', 'threads', 'bluesky', 'bio', 'next_position',
    'next_position_url',
]


def _person_reverse_relations():
    """
    Return ``(fk_rels, m2m_rels)`` — the auto-created reverse relations that
    point at ``Person``, discovered generically from the model meta.

    ``fk_rels`` are reverse foreign keys / one-to-ones (``ManyToOneRel`` /
    ``OneToOneRel``), including the three Position advisor self-references.
    ``m2m_rels`` are reverse many-to-manys (``ManyToManyRel``), e.g. the sorted
    ``authors`` / ``recipients`` sets and the plain ``News.people`` set.
    """
    fk_rels, m2m_rels = [], []
    for field in Person._meta.get_fields():
        if not (field.is_relation and field.auto_created and not field.concrete):
            continue
        if field.many_to_many:
            m2m_rels.append(field)
        elif field.one_to_many or field.one_to_one:
            fk_rels.append(field)
    return fk_rels, m2m_rels


def count_references(person):
    """Total number of objects across all relations pointing at ``person``."""
    fk_rels, m2m_rels = _person_reverse_relations()
    total = 0
    for field in fk_rels:
        total += field.related_model.objects.filter(**{field.field.name: person}).count()
    for field in m2m_rels:
        total += getattr(person, field.get_accessor_name()).count()
    return total


class Command(BaseCommand):
    help = 'Merge duplicate Person records from a reviewed decisions CSV (dry-run by default).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--decisions', required=True,
            help='Path to the decisions CSV (columns: source_id, action, target_id, note).',
        )
        parser.add_argument(
            '--apply', action='store_true',
            help='Actually perform the merges/deletes. Without this flag the command is a dry-run.',
        )

    def handle(self, *args, **options):
        decisions = self._read_decisions(options['decisions'])
        apply = options['apply']

        mode = 'APPLY' if apply else 'DRY-RUN'
        self.stdout.write(f"=== merge_duplicate_people [{mode}] — {len(decisions)} decision(s) ===")

        for row in decisions:
            action = row['action']
            if action == 'merge':
                self._handle_merge(row, apply)
            elif action == 'delete':
                self._handle_delete(row, apply)
            elif action == 'keep':
                self.stdout.write(f"  keep   source={row['source_id']} (namesake / leave alone){self._note(row)}")
            else:
                self.stdout.write(self.style.WARNING(
                    f"  SKIP   unknown action {action!r} for source={row['source_id']}"))

        if not apply:
            self.stdout.write(self.style.WARNING(
                "\nDry-run only — no changes made. Re-run with --apply to perform these actions."))

    # ----- decisions parsing -------------------------------------------------

    def _read_decisions(self, path):
        """Parse and validate the decisions CSV into a list of normalized rows."""
        try:
            with open(path, newline='', encoding='utf-8') as fh:
                rows = list(csv.DictReader(fh))
        except OSError as exc:
            raise CommandError(f"Could not read decisions file {path!r}: {exc}")

        required = {'source_id', 'action'}
        if not rows or not required.issubset({k.strip() for k in rows[0].keys()}):
            raise CommandError(
                "Decisions CSV must have a header row with at least "
                "'source_id' and 'action' columns (plus 'target_id', 'note').")

        cleaned = []
        for i, raw in enumerate(rows, start=2):  # row 1 is the header
            row = {(k or '').strip(): (v or '').strip() for k, v in raw.items()}
            if not row.get('source_id'):
                continue  # allow blank spacer rows
            row['action'] = row.get('action', '').lower()
            if row['action'] == 'merge' and not row.get('target_id'):
                raise CommandError(f"Row {i}: action 'merge' requires a target_id.")
            cleaned.append(row)
        return cleaned

    @staticmethod
    def _note(row):
        return f"  # {row['note']}" if row.get('note') else ''

    # ----- actions -----------------------------------------------------------

    def _handle_merge(self, row, apply):
        source = self._get_person(row['source_id'])
        if source is None:
            self.stdout.write(f"  no-op  source={row['source_id']} already gone (merged?){self._note(row)}")
            return
        target = self._get_person(row['target_id'])
        if target is None:
            self.stdout.write(self.style.ERROR(
                f"  ERROR  target={row['target_id']} not found for source={row['source_id']} — skipping"))
            return
        if source.pk == target.pk:
            self.stdout.write(self.style.ERROR(
                f"  ERROR  source and target are the same person ({source.pk}) — skipping"))
            return

        if not apply:
            self.stdout.write(
                f"  merge  {source.pk} ({source.get_full_name()}, refs={count_references(source)}) "
                f"-> {target.pk} ({target.get_full_name()}, refs={count_references(target)})"
                f"{self._note(row)}")
            return

        with transaction.atomic():
            summary, backfilled = self._merge(source, target)
        moved = ', '.join(f"{k}={v}" for k, v in summary.items()) or 'no related objects'
        backfill = f"; backfilled {', '.join(backfilled)}" if backfilled else ''
        msg = f"merged {row['source_id']} into {target.pk}: {moved}{backfill}"
        self.stdout.write(self.style.SUCCESS(f"  {msg}"))
        _logger.info("merge_duplicate_people: %s", msg)

    def _handle_delete(self, row, apply):
        source = self._get_person(row['source_id'])
        if source is None:
            self.stdout.write(f"  no-op  source={row['source_id']} already gone{self._note(row)}")
            return
        refs = count_references(source)
        if refs != 0:
            self.stdout.write(self.style.ERROR(
                f"  ERROR  refusing to delete {source.pk} ({source.get_full_name()}) — "
                f"has {refs} reference(s); merge it instead"))
            return
        if not apply:
            self.stdout.write(f"  delete {source.pk} ({source.get_full_name()}, refs=0){self._note(row)}")
            return
        source.delete()
        self.stdout.write(self.style.SUCCESS(f"  deleted {row['source_id']} (was a 0-ref shell)"))
        _logger.info("merge_duplicate_people: deleted shell %s", row['source_id'])

    # ----- core merge --------------------------------------------------------

    def _merge(self, source, target):
        """
        Relocate every relation from ``source`` onto ``target``, backfill blank
        scalar fields, then delete ``source``. Returns ``(summary, backfilled)``.
        Must run inside an atomic block.
        """
        fk_rels, m2m_rels = _person_reverse_relations()
        summary = {}

        # Reverse FKs (incl. advisor / co_advisor / grad_mentor self-refs): just
        # repoint the foreign key. SET_NULL/CASCADE on_delete is irrelevant once
        # nothing points at source.
        for field in fk_rels:
            model, fk = field.related_model, field.field.name
            n = model.objects.filter(**{fk: source}).update(**{fk: target})
            if n:
                summary[f"{model.__name__}.{fk}"] = n

        # Reverse M2Ms: rebuild each related object's ordered author/recipient/
        # people list with source swapped for target (dropping source if target
        # is already present — dedup). For SortedManyToManyField, .set() assigns
        # sort_value by list position, so author order is preserved.
        for field in m2m_rels:
            forward = field.field.name  # 'authors' / 'recipients' / 'people'
            moved = 0
            for obj in list(getattr(source, field.get_accessor_name()).all()):
                manager = getattr(obj, forward)
                new_members, seen = [], set()
                for member in manager.all():  # ordered for sorted M2M
                    replacement = target if member.pk == source.pk else member
                    if replacement.pk not in seen:
                        seen.add(replacement.pk)
                        new_members.append(replacement)
                manager.set(new_members)
                moved += 1
            if moved:
                summary[f"{field.related_model.__name__}.{forward}"] = moved

        # Scalar backfill: fill target's blanks from source; never overwrite.
        backfilled = []
        for fld in SCALAR_BACKFILL_FIELDS:
            if not getattr(target, fld) and getattr(source, fld):
                setattr(target, fld, getattr(source, fld))
                backfilled.append(fld)
        if backfilled:
            # Bypass Person.save() (avoids url_name recompute + Star Wars image
            # side effects); we only want the scalar columns written.
            Person.objects.filter(pk=target.pk).update(
                **{fld: getattr(target, fld) for fld in backfilled})

        # Delete the now-orphaned source. Its pre_delete signal removes source's
        # own image file (target's image is untouched, so nothing shared breaks).
        source.delete()
        return summary, backfilled

    @staticmethod
    def _get_person(pk):
        if not pk:
            return None
        try:
            return Person.objects.get(pk=int(pk))
        except (Person.DoesNotExist, ValueError):
            return None
