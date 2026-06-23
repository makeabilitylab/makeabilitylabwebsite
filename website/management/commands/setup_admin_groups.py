import logging
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

# The four auto-generated Django model permissions (add/change/delete/view).
CRUD = ("add", "change", "delete", "view")

# ---------------------------------------------------------------------------
# Permission specs (issue #1125 — "Users = people, Groups = roles").
#
# We deliberately stopped using shared, role-named *user* accounts (gradmin,
# ugradmin, collabmin) as if they were groups. Instead, individuals get personal
# accounts assigned to one of these two groups; the superuser flag (you, plus a
# break-glass backup) covers everything a group cannot.
#
# Each spec maps (app_label, model_name) -> tuple of actions to grant.
# ---------------------------------------------------------------------------

# Editors — PhD students and long-term staff who maintain the site. Full content
# management on the public-facing models. DELIBERATELY EXCLUDES:
#   - grant, award         -> admin-only by decision (funding data / curated
#                             external recognitions stay with the superuser)
#   - user/group/permission/logentry/session -> no account administration
#                             outside the superuser
#   - contenttype, easy_thumbnails.* -> infra/cache tables nobody hand-edits
#                             (these were collateral on the old gradmin account)
EDITORS_MODELS = [
    "banner", "person", "position", "project", "keyword", "talk",
    "publication", "poster", "news", "video",
    "photo", "projectumbrella", "sponsor", "projectrole",
]
EDITORS_SPEC = {("website", model): CRUD for model in EDITORS_MODELS}

# Contributors — undergrads / interns (shared `contributor` account, or a personal
# account promoted to Editors if they become a regular maintainer). Narrowest
# useful tier: edit bios, and add (with view) on the main artifacts so they can
# submit their own work AND review what they submitted, but never change or delete
# anyone else's. NO deletes anywhere. This merges the two real shapes the legacy
# accounts had: ugradmin (Person add/change/view) and collabmin (add across
# artifacts), plus `view` so the changelist is reachable after an add (without it
# Django bounces them to the admin index with no way to see their own entry).
CONTRIBUTORS_SPEC = {
    ("website", "person"): ("add", "change", "view"),
    ("website", "publication"): ("add", "view"),
    ("website", "talk"): ("add", "view"),
    ("website", "poster"): ("add", "view"),
    ("website", "projectrole"): ("add", "view"),
}

GROUPS = {
    "Editors": EDITORS_SPEC,
    "Contributors": CONTRIBUTORS_SPEC,
}


class Command(BaseCommand):
    help = (
        "Create/refresh the Editors and Contributors admin groups with their "
        "intended permission sets (issue #1125). Idempotent: each run sets each "
        "group's permissions to exactly the spec below — extra permissions added "
        "by hand are REMOVED and missing ones are added, so this command is the "
        "source of truth for these two groups. It does NOT create user accounts, "
        "assign users to groups, or touch the superuser flag; do that in /admin. "
        "Run with --dry-run first to preview changes."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without writing to the database.",
        )

    def _resolve_perms(self, spec):
        """Turn a {(app_label, model): (actions,)} spec into a set of Permission
        objects, warning (not failing) on any codename/content type that can't be
        found so a single typo or missing model never aborts the whole run."""
        perms = set()
        for (app_label, model_name), actions in spec.items():
            try:
                content_type = ContentType.objects.get(
                    app_label=app_label, model=model_name
                )
            except ContentType.DoesNotExist:
                _logger.warning(
                    f"setup_admin_groups: no content type for "
                    f"{app_label}.{model_name} — skipping (is the model migrated?)"
                )
                continue
            for action in actions:
                codename = f"{action}_{model_name}"
                try:
                    perms.add(
                        Permission.objects.get(
                            content_type=content_type, codename=codename
                        )
                    )
                except Permission.DoesNotExist:
                    _logger.warning(
                        f"setup_admin_groups: no permission '{codename}' for "
                        f"{app_label}.{model_name} — skipping."
                    )
        return perms

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        _logger.debug(f"Running setup_admin_groups.py (dry_run={dry_run})")

        for group_name, spec in GROUPS.items():
            desired = self._resolve_perms(spec)

            if dry_run:
                group = Group.objects.filter(name=group_name).first()
                current = set(group.permissions.all()) if group else set()
            else:
                group, created = Group.objects.get_or_create(name=group_name)
                if created:
                    _logger.info(f"Created group '{group_name}'")
                current = set(group.permissions.all())

            to_add = desired - current
            to_remove = current - desired

            for perm in sorted(to_add, key=lambda p: p.codename):
                _logger.info(
                    f"[{'dry-run' if dry_run else 'apply'}] {group_name}: "
                    f"+ {perm.codename}"
                )
            for perm in sorted(to_remove, key=lambda p: p.codename):
                _logger.info(
                    f"[{'dry-run' if dry_run else 'apply'}] {group_name}: "
                    f"- {perm.codename}"
                )

            if not dry_run:
                # set() makes the group match the spec exactly (idempotent).
                group.permissions.set(desired)

            verb = "Would set" if dry_run else "Set"
            _logger.info(
                f"setup_admin_groups: {verb} '{group_name}' to "
                f"{len(desired)} permission(s) "
                f"(+{len(to_add)} / -{len(to_remove)})."
            )

        _logger.debug("Completed setup_admin_groups.py")
