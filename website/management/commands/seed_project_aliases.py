import logging
from django.core.management.base import BaseCommand
from website.models import Project, ProjectAlias

_logger = logging.getLogger(__name__)

# Historical project renames that predate the auto-capture in Project.save()
# (#944). Each entry maps a *former* slug to the project's *current* slug. Going
# forward, renames record their own aliases automatically; this list only
# backfills the ones that already happened.
#
# Keep keys/values lowercase (slugs are matched case-insensitively). The command
# is idempotent and safe to run on every deploy: it skips any entry whose target
# project doesn't exist or whose old slug is already a live project.
#
# Current slugs confirmed against prod 2026-06-23.
#
# smarthomedhh -> homesound was renamed in the admin *before* the auto-capture in
# Project.save() shipped, so no alias was recorded and /project/smarthomedhh/
# 404s. It's backfilled here. (Renames done after this feature deploys capture
# their own aliases automatically and don't need an entry.)
HISTORICAL_ALIASES = {
    'mapoutloud': 'geovisally',
    'mixed-ability-art': 'artinsight',
    'smarthomedhh': 'homesound',
}


class Command(BaseCommand):
    help = ("Idempotently backfills ProjectAlias rows for known historical project "
            "renames so their old /project/<slug>/ URLs 301-redirect (#944).")

    def handle(self, *args, **options):
        created, skipped = 0, 0
        for old_slug, current_slug in HISTORICAL_ALIASES.items():
            old_slug = old_slug.strip().lower()
            current_slug = current_slug.strip().lower()

            # Don't shadow a live project: if the old slug now resolves to a real
            # project, an alias for it would be dead (the live project always wins).
            if Project.objects.filter(short_name__iexact=old_slug).exists():
                _logger.info(f"seed_project_aliases: '{old_slug}' is a live slug; skipping.")
                skipped += 1
                continue

            project = Project.objects.filter(short_name__iexact=current_slug).first()
            if project is None:
                _logger.warning(
                    f"seed_project_aliases: target project '{current_slug}' not found; "
                    f"skipping alias '{old_slug}'.")
                skipped += 1
                continue

            alias, was_created = ProjectAlias.objects.get_or_create(
                slug=old_slug, defaults={'project': project})
            if was_created:
                _logger.info(f"seed_project_aliases: created alias {old_slug} → {current_slug}")
                created += 1
            else:
                # Repoint if an existing alias drifted to the wrong project.
                if alias.project_id != project.id:
                    alias.project = project
                    alias.save()
                    _logger.info(f"seed_project_aliases: repointed alias {old_slug} → {current_slug}")
                skipped += 1

        self.stdout.write(f"seed_project_aliases: {created} created, {skipped} skipped.")
