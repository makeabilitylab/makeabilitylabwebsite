"""Tests for project slug renames → 301 redirects via ProjectAlias (#944).

Covers the four moving parts:
  - Project.save() auto-captures the old slug as a ProjectAlias on rename.
  - The project view 301-redirects a retired slug to the project's current URL.
  - Reclaiming a slug clears its alias (no self-redirect loop).
  - clean() keeps the live-slug + alias namespace unique.
  - The seed_project_aliases backfill command is idempotent.
"""

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.urls import reverse

from website.models import Project, ProjectAlias
from website.tests.base import DatabaseTestCase


class ProjectRenameAutoCaptureTests(DatabaseTestCase):
    """Project.save() records the previous slug as a redirecting alias (#944)."""

    def test_rename_creates_alias_for_old_slug(self):
        project = self.make_project(name="Map Out Loud", short_name="mapoutloud")
        project.short_name = "geovisally"
        project.save()

        aliases = ProjectAlias.objects.filter(project=project).values_list('slug', flat=True)
        self.assertIn("mapoutloud", aliases)
        # The current slug must NOT be an alias of itself.
        self.assertNotIn("geovisally", aliases)

    def test_rename_is_case_insensitive_noop(self):
        """Changing only the case of the slug is not a rename — no alias created."""
        project = self.make_project(name="Sidewalk", short_name="projectsidewalk")
        project.short_name = "ProjectSidewalk"
        project.save()
        self.assertEqual(ProjectAlias.objects.filter(project=project).count(), 0)

    def test_creating_a_project_makes_no_alias(self):
        project = self.make_project(name="Fresh", short_name="fresh")
        self.assertEqual(ProjectAlias.objects.filter(project=project).count(), 0)


class ProjectAliasRedirectViewTests(DatabaseTestCase):
    """The project view 301-redirects retired slugs to the current page."""

    def test_old_slug_301_redirects_to_current(self):
        project = self.make_project(name="Map Out Loud", short_name="mapoutloud",
                                    is_visible=True)
        project.short_name = "geovisally"
        project.save()

        resp = self.client.get("/project/mapoutloud/")
        self.assertRedirects(resp, "/project/geovisally/",
                             status_code=301, target_status_code=200)

    def test_unknown_slug_still_404s(self):
        resp = self.client.get("/project/doesnotexistanywhere/")
        self.assertEqual(resp.status_code, 404)

    def test_live_slug_wins_over_alias(self):
        """A reclaimed slug serves the live project (200), not a redirect."""
        # A: foo -> bar, leaving alias 'foo' -> A
        a = self.make_project(name="Alpha", short_name="foo", is_visible=True)
        a.short_name = "bar"
        a.save()
        # B reclaims 'foo'
        b = self.make_project(name="Beta", short_name="baz", is_visible=True)
        b.short_name = "foo"
        b.save()

        self.assertFalse(ProjectAlias.objects.filter(slug="foo").exists())
        resp = self.client.get("/project/foo/")
        self.assertEqual(resp.status_code, 200)          # serves B, no redirect
        # B's previous slug now redirects to foo
        resp_baz = self.client.get("/project/baz/")
        self.assertRedirects(resp_baz, "/project/foo/",
                             status_code=301, target_status_code=200)

    def test_alias_to_private_project_redirects_then_404s_for_anon(self):
        """Resolution still honors visibility: the redirect lands, but a private
        target 404s for anonymous visitors (#1300)."""
        project = self.make_project(name="Secret", short_name="secretnow", is_visible=False)
        ProjectAlias.objects.create(slug="secretold", project=project)

        resp = self.client.get("/project/secretold/")
        self.assertEqual(resp.status_code, 301)
        self.assertEqual(resp["Location"], "/project/secretnow/")
        self.assertEqual(self.client.get("/project/secretnow/").status_code, 404)


class SlugNamespaceUniquenessTests(DatabaseTestCase):
    """clean() keeps live slugs and aliases from colliding (#944)."""

    def test_project_short_name_cannot_collide_with_other_projects_alias(self):
        a = self.make_project(name="Alpha", short_name="foo")
        a.short_name = "bar"
        a.save()  # alias 'foo' -> A now exists

        dupe = Project(name="Gamma", short_name="foo")
        with self.assertRaises(ValidationError) as ctx:
            dupe.full_clean()
        self.assertIn("short_name", ctx.exception.message_dict)

    def test_project_may_reclaim_its_own_former_slug(self):
        a = self.make_project(name="Alpha", short_name="foo")
        a.short_name = "bar"
        a.save()  # alias 'foo' -> A
        a.short_name = "foo"
        a.full_clean()  # reclaiming our own former slug must not raise

    def test_alias_cannot_equal_a_live_slug(self):
        live = self.make_project(name="Live", short_name="liveslug")
        other = self.make_project(name="Other", short_name="otherslug")
        bad = ProjectAlias(slug="liveslug", project=other)
        with self.assertRaises(ValidationError) as ctx:
            bad.full_clean()
        self.assertIn("slug", ctx.exception.message_dict)

    def test_alias_cannot_duplicate_another_projects_alias(self):
        a = self.make_project(name="Alpha", short_name="alpha")
        b = self.make_project(name="Beta", short_name="beta")
        ProjectAlias.objects.create(slug="shared", project=a)
        dupe = ProjectAlias(slug="shared", project=b)
        with self.assertRaises(ValidationError) as ctx:
            dupe.full_clean()
        self.assertIn("slug", ctx.exception.message_dict)


class SeedProjectAliasesCommandTests(DatabaseTestCase):
    """seed_project_aliases backfills historical renames idempotently (#944)."""

    def test_seed_creates_known_alias_and_is_idempotent(self):
        # Matches the confirmed HISTORICAL_ALIASES entry mapoutloud -> geovisally.
        self.make_project(name="GeoVisA11y", short_name="geovisally")

        call_command("seed_project_aliases")
        call_command("seed_project_aliases")  # second run must not duplicate

        self.assertEqual(ProjectAlias.objects.filter(slug="mapoutloud").count(), 1)

    def test_seed_skips_when_target_project_missing(self):
        # No 'geovisally' project exists → nothing to point at, so no alias.
        call_command("seed_project_aliases")
        self.assertFalse(ProjectAlias.objects.filter(slug="mapoutloud").exists())
