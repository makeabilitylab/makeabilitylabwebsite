import logging

from django.core.management.base import BaseCommand

from website.models import Talk, Poster, Publication
import website.utils.ml_utils as ml_utils

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Normalizes artifact forum names by stripping a trailing year (and a "
        "leading 'Proceedings of'), per the model's rule that forum_name should "
        "not include the year (the date is stored separately). Originally this "
        "ran on Publications only, which is why historical Talk/Poster forum "
        "names still embed the year (e.g. 'ASSETS 2016') and the standardized "
        "filename scheme then doubled it ('...ASSETS20162016'). This now covers "
        "Talk, Poster, and Publication (#1390). "
        "Writes via QuerySet.update() rather than Model.save() ON PURPOSE: "
        "save() would notice the changed forum_name produces a new standardized "
        "filename and rename the files on disk as a side effect, which must stay "
        "under the separately-gated restandardize_artifact_filenames step. "
        "update() touches only the forum_name column. Idempotent (a cleaned "
        "name has no trailing year, so a re-run is a no-op) and safe to run on "
        "every container start."
    )

    # The concrete artifact models whose forum_name we normalize.
    MODELS = (Talk, Poster, Publication)

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without writing to the database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        _logger.debug(
            f"Running remove_year_from_forum_name.py (dry_run={dry_run}) to "
            f"strip trailing years from forum names."
        )

        total_changed = 0
        for model in self.MODELS:
            total_changed += self._clean_model(model, dry_run)

        verb = "Would change" if dry_run else "Changed"
        model_names = ", ".join(m.__name__ for m in self.MODELS)
        _logger.info(
            f"remove_year_from_forum_name: {verb} {total_changed} forum "
            f"name(s) across {model_names}."
        )
        _logger.debug("Completed remove_year_from_forum_name.py")

    def _clean_model(self, model, dry_run):
        """Normalize forum_name for every row of one artifact model.

        Returns the number of rows changed (or that would change in dry-run).
        Uses ``QuerySet.update()`` so no ``Model.save()`` runs — that keeps file
        renaming out of this step (see the class docstring) and avoids the m2m /
        thumbnail work ``save()`` would otherwise do for a forum-name-only edit.
        """
        num_changed = 0
        for obj in model.objects.all():
            old_forum_name = obj.forum_name
            new_forum_name = ml_utils.clean_forum_name(old_forum_name)

            # clean_forum_name() returns "" for a None/empty input; guard so we
            # never overwrite a genuine value with an empty string (e.g. a
            # forum_name that is itself just a bare year).
            if not new_forum_name or old_forum_name == new_forum_name:
                continue

            # Log at INFO (not DEBUG) so the change is visible on prod, where the
            # file log handler runs at INFO when DEBUG is off. This is what lets
            # us review exactly which forum names changed in debug.log.
            action = "dry-run" if dry_run else "apply"
            _logger.info(
                f"[{action}] {model.__name__} id={obj.pk}: forum_name "
                f"'{old_forum_name}' -> '{new_forum_name}'"
            )
            if not dry_run:
                model.objects.filter(pk=obj.pk).update(forum_name=new_forum_name)
            num_changed += 1

        return num_changed
