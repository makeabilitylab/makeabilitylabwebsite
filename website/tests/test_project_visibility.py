"""
Tests for the Project ``is_visible`` flag (issue #1300).

Visibility used to be an implicit "has a thumbnail AND a publication" heuristic
duplicated across views and templates. It's now a single editor-controlled flag:
new projects start private, and a one-shot backfill preserves the visibility of
projects that predate the column. These tests pin:

  * new projects default to private (set in Project.save());
  * can_show_online() reflects is_visible;
  * the backfill resolves only legacy NULL rows and is idempotent;
  * the public gallery / landing page / individual page honor the flag, while
    logged-in staff can still preview a private project page.
"""

from datetime import date

from django.contrib.auth.models import User
from django.core.management import call_command
from django.urls import reverse

from website.models import Project
from website.models.project_role import ProjectRole
from website.tests.base import DatabaseTestCase


def _set_legacy_null(project):
    """
    Force a project's is_visible back to NULL to simulate a row that predates
    the column. Project.save() defaults new projects to False, so we write the
    NULL directly via the queryset (which bypasses save()).
    """
    Project.objects.filter(pk=project.pk).update(is_visible=None)
    project.refresh_from_db()


class ProjectVisibilityDefaultTests(DatabaseTestCase):
    """New projects are private by default; the default is set in save()."""

    def test_new_project_defaults_to_private(self):
        project = self.make_project(name="Fresh Project")
        self.assertFalse(project.is_visible)

    def test_explicit_visible_is_respected(self):
        project = self.make_project(name="Public Project", is_visible=True)
        self.assertTrue(project.is_visible)

    def test_save_does_not_override_existing_value(self):
        """Re-saving a project must not reset a manually-set visibility."""
        project = self.make_project(name="Toggled", is_visible=True)
        project.is_visible = False
        project.save()
        project.refresh_from_db()
        self.assertFalse(project.is_visible)

    def test_can_show_online_reflects_flag(self):
        visible = self.make_project(name="Shown", is_visible=True)
        hidden = self.make_project(name="Hidden", is_visible=False)
        self.assertTrue(visible.can_show_online())
        self.assertFalse(hidden.can_show_online())

    def test_can_show_online_treats_null_as_private(self):
        project = self.make_project(name="Legacy")
        _set_legacy_null(project)
        self.assertFalse(project.can_show_online())


class BackfillProjectVisibilityTests(DatabaseTestCase):
    """
    backfill_project_visibility resolves legacy NULL rows using the old
    thumbnail+publication criteria and leaves already-decided rows alone.
    """

    def _add_publication(self, project):
        pub = self.make_publication(title=f"Pub for {project.name}")
        pub.projects.add(project)
        return pub

    def test_null_with_thumbnail_and_pub_becomes_visible(self):
        project = self.make_project(name="Complete Legacy", with_thumbnail=True)
        self._add_publication(project)
        _set_legacy_null(project)

        call_command("backfill_project_visibility")
        project.refresh_from_db()
        self.assertTrue(project.is_visible)

    def test_null_missing_thumbnail_becomes_private(self):
        project = self.make_project(name="No Thumb Legacy")
        self._add_publication(project)
        _set_legacy_null(project)

        call_command("backfill_project_visibility")
        project.refresh_from_db()
        self.assertFalse(project.is_visible)

    def test_null_missing_publication_becomes_private(self):
        project = self.make_project(name="No Pub Legacy", with_thumbnail=True)
        _set_legacy_null(project)

        call_command("backfill_project_visibility")
        project.refresh_from_db()
        self.assertFalse(project.is_visible)

    def test_already_set_values_are_not_clobbered(self):
        """
        A complete project an admin deliberately hid (is_visible=False) must
        stay hidden across a backfill re-run — the command only touches NULLs.
        """
        project = self.make_project(
            name="Admin Hidden", with_thumbnail=True, is_visible=False
        )
        self._add_publication(project)

        call_command("backfill_project_visibility")
        project.refresh_from_db()
        self.assertFalse(project.is_visible)

    def test_dry_run_makes_no_changes(self):
        project = self.make_project(name="Dry Legacy", with_thumbnail=True)
        self._add_publication(project)
        _set_legacy_null(project)

        call_command("backfill_project_visibility", "--dry-run")
        project.refresh_from_db()
        self.assertIsNone(project.is_visible)


class ProjectListingVisibilityTests(DatabaseTestCase):
    """The public project gallery shows only is_visible=True projects."""

    def _make_listed_project(self, name, is_visible, end_date=None):
        project = self.make_project(
            name=name, with_thumbnail=True, is_visible=is_visible,
            start_date=date(2020, 1, 1), end_date=end_date,
        )
        pub = self.make_publication(title=f"Pub for {name}")
        pub.projects.add(project)
        return project

    def test_visible_active_project_appears(self):
        self._make_listed_project("Visible Active", is_visible=True)
        response = self.client.get(reverse("website:projects"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Visible Active")

    def test_private_project_hidden_even_with_thumbnail_and_pub(self):
        self._make_listed_project("Secret Active", is_visible=False)
        response = self.client.get(reverse("website:projects"))
        self.assertNotContains(response, "Secret Active")

    def test_visible_completed_project_appears(self):
        self._make_listed_project(
            "Visible Done", is_visible=True, end_date=date(2021, 1, 1)
        )
        response = self.client.get(reverse("website:projects"))
        self.assertContains(response, "Visible Done")


class IndividualProjectPageVisibilityTests(DatabaseTestCase):
    """
    A private project's page 404s for the public but is previewable by staff.
    """

    def _make_project(self, is_visible):
        return self.make_project(
            name="Stealth Project", short_name="stealthproject",
            is_visible=is_visible, start_date=date(2020, 1, 1),
        )

    def test_private_project_404_for_anonymous(self):
        project = self._make_project(is_visible=False)
        response = self.client.get(
            reverse("website:project", kwargs={"project_name": project.short_name})
        )
        self.assertEqual(response.status_code, 404)

    def test_private_project_visible_to_staff(self):
        project = self._make_project(is_visible=False)
        staff = User.objects.create_user(
            username="admin", password="pw", is_staff=True
        )
        self.client.force_login(staff)
        response = self.client.get(
            reverse("website:project", kwargs={"project_name": project.short_name})
        )
        self.assertEqual(response.status_code, 200)

    def test_visible_project_200_for_anonymous(self):
        project = self._make_project(is_visible=True)
        response = self.client.get(
            reverse("website:project", kwargs={"project_name": project.short_name})
        )
        self.assertEqual(response.status_code, 200)


# --- Secondary surfaces: nothing should mention a private project --------


class AwardVisibleProjectsTests(DatabaseTestCase):
    """Award.get_visible_projects (used by the public awards snippet) excludes private projects."""

    def test_only_visible_projects_returned(self):
        from website.models import Award
        visible = self.make_project(name="Award Visible", is_visible=True)
        private = self.make_project(name="Award Private", is_visible=False)
        award = Award.objects.create(title="Best Paper", date=date(2024, 1, 1))
        award.projects.add(visible, private)

        names = {p.name for p in award.get_visible_projects()}
        self.assertEqual(names, {"Award Visible"})


class PersonProjectsContribVisibilityTests(DatabaseTestCase):
    """get_projects_sorted_by_contrib (public People page) excludes private projects."""

    def _link(self, person, project):
        ProjectRole.objects.create(
            project=project, person=person, start_date=date(2024, 1, 1)
        )
        pub = self.make_publication(title=f"Pub {project.name}")
        pub.authors.add(person)
        pub.projects.add(project)

    def test_private_project_excluded(self):
        person = self.make_person(first_name="Grace", last_name="Hopper")
        visible = self.make_project(name="Contrib Visible", is_visible=True)
        private = self.make_project(name="Contrib Private", is_visible=False)
        self._link(person, visible)
        self._link(person, private)

        names = {p.name for p in person.get_projects_sorted_by_contrib()}
        self.assertEqual(names, {"Contrib Visible"})


class LandingBannerVisibilityTests(DatabaseTestCase):
    """get_landing_page_banners drops banners tied to a private project."""

    def test_private_project_banner_excluded_but_projectless_kept(self):
        from website.models import Banner
        from website.views.index import get_landing_page_banners

        private = self.make_project(name="Banner Private", is_visible=False)
        visible = self.make_project(name="Banner Visible", is_visible=True)
        private_banner = Banner.objects.create(
            title="Private Banner", landing_page=True, favorite=True, project=private
        )
        visible_banner = Banner.objects.create(
            title="Visible Banner", landing_page=True, favorite=True, project=visible
        )
        projectless_banner = Banner.objects.create(
            title="Projectless Banner", landing_page=True, favorite=True
        )

        returned = set(get_landing_page_banners(10))
        self.assertIn(visible_banner, returned)
        self.assertIn(projectless_banner, returned)
        self.assertNotIn(private_banner, returned)


class ProjectListingUmbrellaFilterVisibilityTests(DatabaseTestCase):
    """The umbrella filter counts/names only publicly-visible projects."""

    def test_private_project_excluded_from_umbrella_map(self):
        from website.models import ProjectUmbrella
        umbrella = ProjectUmbrella.objects.create(
            name="Accessibility", short_name="a11y"
        )
        for name, vis in [("U Visible", True), ("U Private", False)]:
            project = self.make_project(
                name=name, with_thumbnail=True, is_visible=vis,
                start_date=date(2020, 1, 1),
            )
            project.project_umbrellas.add(umbrella)
            pub = self.make_publication(title=f"Pub {name}")
            pub.projects.add(project)

        response = self.client.get(reverse("website:projects"))
        umbrella_map = response.context["map_project_umbrella_to_projects"]
        self.assertEqual(umbrella_map.get("a11y"), ["U Visible"])


class NewsItemRelatedProjectsVisibilityTests(DatabaseTestCase):
    """The news item page lists only publicly-visible related projects."""

    def test_private_related_project_hidden(self):
        visible = self.make_project(name="News Visible Proj", is_visible=True,
                                    start_date=date(2020, 1, 1))
        private = self.make_project(name="News Private Proj", is_visible=False,
                                    start_date=date(2020, 1, 1))
        news = self.make_news_item(title="A Discovery")
        news.project.add(visible, private)

        response = self.client.get(
            reverse("website:news_item_by_id", kwargs={"id": news.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "News Visible Proj")
        self.assertNotContains(response, "News Private Proj")
