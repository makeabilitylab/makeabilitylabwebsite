from django.db import models
from django.core.exceptions import ValidationError

from .project import Project

import logging

_logger = logging.getLogger(__name__)


class ProjectAlias(models.Model):
    """A retired URL slug that should redirect to a project's current page.

    Projects occasionally get renamed to a *completely different* name (e.g.
    MapOutLoud -> GeoVisA11y), which also changes ``Project.short_name`` (the URL
    slug). Without a record of the old slug, the previous URL hard-404s and any
    external links / search-engine results to it break (#944, surfaced in the
    #1142 SEO audit).

    Each ``ProjectAlias`` maps one old slug -> one project. The project view
    (``website/views/project.py``) consults this table when a slug doesn't match
    a live project and issues a permanent (301) redirect to the current slug.
    Rows are created automatically by ``Project.save()`` when a slug changes, and
    can also be added by hand via the admin inline or seeded by the
    ``seed_project_aliases`` management command for historical renames.

    Uniqueness: the slug namespace spans *both* live ``Project.short_name`` values
    and these aliases. ``clean()`` enforces that a slug collides with neither, so
    a slug always resolves to exactly one destination (no ambiguous redirects).
    The live project always wins resolution, so an alias equal to a live slug
    would be dead — hence it's rejected.
    """

    slug = models.CharField(max_length=255, db_index=True)
    slug.help_text = ("A former URL slug for this project (lowercase, no spaces). Visiting "
                      "/project/<this-slug>/ will 301-redirect to the project's current page.")

    project = models.ForeignKey(Project, related_name='aliases', on_delete=models.CASCADE)

    created = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = "Project slug alias"
        verbose_name_plural = "Project slug aliases"

    def __str__(self):
        return f"{self.slug} → {self.project.short_name}"

    def save(self, *args, **kwargs):
        # Normalize so lookups (always done via __iexact, but stored lowercase for
        # consistency) and the redirect target are predictable.
        if self.slug:
            self.slug = self.slug.strip().lower()
        super().save(*args, **kwargs)

    def clean(self):
        """Keep the combined (live slug + alias) namespace unique, case-insensitively.

        Rejects a slug that (a) matches any live ``Project.short_name`` — the live
        project would always win resolution, making the alias dead — or (b) matches
        another ``ProjectAlias`` for a different destination.
        """
        super().clean()
        if not self.slug:
            raise ValidationError({'slug': 'A slug is required.'})

        slug = self.slug.strip().lower()

        if Project.objects.filter(short_name__iexact=slug).exists():
            raise ValidationError({
                'slug': (f'"{slug}" is already a live project slug, so an alias for it would '
                         f'never be used. Aliases are only for *former* slugs.')
            })

        clash = ProjectAlias.objects.filter(slug__iexact=slug)
        if self.pk:
            clash = clash.exclude(pk=self.pk)
        clash = clash.exclude(project=self.project)
        if clash.exists():
            raise ValidationError({
                'slug': f'The alias "{slug}" already points to a different project.'
            })
