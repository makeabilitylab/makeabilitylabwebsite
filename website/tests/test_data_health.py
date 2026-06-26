"""
Tests for the Data Health admin dashboard + checks (issue #1276).

Covers the shared name/image helpers, superuser gating on the dashboard /
detail / export views, the CSV export, each individual check's row logic, and
the read-only guarantee (checks must never mutate the DB).
"""

import os
import shutil
import tempfile

from django.contrib.auth.models import User
from django.test import SimpleTestCase, override_settings
from django.urls import reverse

from website.admin.data_health.registry import REGISTRY, HealthCheck, get_check
from website.tests.base import DatabaseTestCase
from website.utils.name_utils import normalize_person_name, is_default_person_image


class NameUtilsTests(SimpleTestCase):
    """Unit tests for the shared name/image helpers (no DB)."""

    def test_normalize_folds_accents_and_strips_nonalpha(self):
        self.assertEqual(normalize_person_name("Jon", "Froehlich"), "jonfroehlich")
        self.assertEqual(normalize_person_name("Renée", "O'Brien"), "reneeobrien")
        self.assertEqual(normalize_person_name("Jon-Paul", "Smith Jr."), "jonpaulsmithjr")

    def test_same_name_different_case_same_key(self):
        self.assertEqual(
            normalize_person_name("Jane", "Doe"),
            normalize_person_name("jane", "doe"),
        )

    def test_default_image_detection(self):
        self.assertTrue(is_default_person_image(None))

        class _Empty:
            name = ""

        class _StarWars:
            name = "person/jane_doe_easteregg_starwars_rebel.png"

        class _Real:
            name = "person/jane_doe.gif"

        self.assertTrue(is_default_person_image(_Empty()))
        self.assertTrue(is_default_person_image(_StarWars()))
        self.assertFalse(is_default_person_image(_Real()))


class DataHealthAuthTests(DatabaseTestCase):
    """Superuser gating on the dashboard, detail, and export views."""

    def setUp(self):
        self.superuser = User.objects.create_superuser("root", "r@example.com", "pw")
        self.staff = User.objects.create_user(
            "staffer", "s@example.com", "pw", is_staff=True
        )

    def test_superuser_can_view_dashboard(self):
        self.client.force_login(self.superuser)
        resp = self.client.get(reverse("admin:data_health_dashboard"))
        self.assertEqual(resp.status_code, 200)

    def test_staff_nonsuperuser_forbidden(self):
        self.client.force_login(self.staff)
        for name, args in [
            ("admin:data_health_dashboard", []),
            ("admin:data_health_detail", ["duplicate-people"]),
            ("admin:data_health_export", ["duplicate-people"]),
        ]:
            resp = self.client.get(reverse(name, args=args))
            self.assertEqual(resp.status_code, 403, msg=name)

    def test_anonymous_redirected_to_login(self):
        resp = self.client.get(reverse("admin:data_health_dashboard"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/admin/login/", resp["Location"])

    def test_unknown_check_returns_404(self):
        self.client.force_login(self.superuser)
        resp = self.client.get(reverse("admin:data_health_detail", args=["nope"]))
        self.assertEqual(resp.status_code, 404)


class DataHealthCsvTests(DatabaseTestCase):
    """The CSV export streams text/csv as an attachment with the right rows."""

    def setUp(self):
        self.superuser = User.objects.create_superuser("root", "r@example.com", "pw")
        self.client.force_login(self.superuser)

    def test_csv_headers_and_content(self):
        self.make_person(first_name="Jane", last_name="Doe", email="jane@example.com")
        self.make_person(first_name="Jane", last_name="Doe", email="jane2@example.com")
        resp = self.client.get(
            reverse("admin:data_health_export", args=["duplicate-people"])
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "text/csv")
        self.assertIn(
            'attachment; filename="duplicate-people-', resp["Content-Disposition"]
        )
        body = resp.content.decode()
        self.assertIn("cluster_key", body)  # header row
        self.assertIn("jane@example.com", body)
        self.assertIn("jane2@example.com", body)


class DuplicatePeopleCheckTests(DatabaseTestCase):
    def test_clusters_only_multi_person_same_name(self):
        self.make_person(first_name="Jane", last_name="Doe")
        self.make_person(first_name="Jane", last_name="Doe")
        self.make_person(first_name="John", last_name="Smith")  # unique
        rows = get_check("duplicate-people").get_rows()
        self.assertEqual({r["cluster_key"] for r in rows}, {"janedoe"})
        self.assertEqual(len(rows), 2)

    def test_total_refs_counts_relations(self):
        p1 = self.make_person(first_name="Jane", last_name="Doe")
        p2 = self.make_person(first_name="Jane", last_name="Doe")
        pub = self.make_publication(title="A Counted Paper")
        pub.authors.add(p1)
        rows = {r["id"]: r for r in get_check("duplicate-people").get_rows()}
        self.assertEqual(rows[p1.pk]["pub_count"], 1)
        self.assertEqual(rows[p1.pk]["total_refs"], 1)
        self.assertEqual(rows[p2.pk]["total_refs"], 0)  # safe-to-delete shell

    def test_clean_data_no_rows(self):
        self.make_person(first_name="Solo", last_name="Person")
        self.assertEqual(get_check("duplicate-people").get_rows(), [])


class UrlNameCollisionsCheckTests(DatabaseTestCase):
    def test_detects_forced_collision_and_placeholder(self):
        from website.models import Person

        self.make_person(first_name="Jane", last_name="Doe")
        p2 = self.make_person(first_name="Jane", last_name="Doe")  # -> janedoe2
        p3 = self.make_person(first_name="Solo", last_name="One")
        # save() auto-dedupes url_name, so force a historical collision directly.
        Person.objects.filter(pk=p2.pk).update(url_name="janedoe")
        Person.objects.filter(pk=p3.pk).update(url_name="placeholder")

        rows = {r["url_name"]: r for r in get_check("url-name-collisions").get_rows()}
        self.assertIn("janedoe", rows)
        self.assertEqual(rows["janedoe"]["count"], 2)
        self.assertIn("placeholder", rows)


class PublicationQualityCheckTests(DatabaseTestCase):
    def test_duplicate_titles_and_missing_venue(self):
        self.make_publication(title="Dup Paper")
        self.make_publication(title="Dup Paper")  # duplicate normalized title
        self.make_publication(title="No Venue Paper", forum_name=None)
        rows = {r["id"]: r for r in get_check("publication-quality").get_rows()}
        self.assertEqual(len([r for r in rows.values() if r["dup_title"]]), 2)
        self.assertTrue(
            any("forum_name" in r["missing_fields"] for r in rows.values())
        )


class ProjectHealthCheckTests(DatabaseTestCase):
    def test_flags_incomplete_project(self):
        from website.models import Project

        Project.objects.create(name="Lonely Project", short_name="lonely")
        rows = {r["name"]: r for r in get_check("project-health").get_rows()}
        self.assertIn("Lonely Project", rows)
        self.assertIn("no thumbnail", rows["Lonely Project"]["issues"])
        self.assertIn("no publication", rows["Lonely Project"]["issues"])


class ProjectLeadershipCheckTests(DatabaseTestCase):
    def _add_role(self, project, lead_role, start_date, end_date=None):
        from website.models import ProjectRole

        person = self.make_person(first_name="Lead", last_name="Person")
        return ProjectRole.objects.create(
            person=person,
            project=project,
            lead_project_role=lead_role,
            start_date=start_date,
            end_date=end_date,
        )

    def test_flags_project_with_no_pi(self):
        proj = self.make_project(name="PI-less Project")
        rows = {r["name"]: r for r in get_check("project-leadership").get_rows()}
        self.assertIn("PI-less Project", rows)
        self.assertEqual(rows["PI-less Project"]["issues"], "no PI")
        self.assertEqual(rows["PI-less Project"]["pi_count"], 0)

    def test_ongoing_project_with_only_an_ended_pi_flagged_no_active_pi(self):
        from datetime import date, timedelta
        from website.models.project_role import LeadProjectRoleTypes

        proj = self.make_project(name="Stale Lead Project")  # no end_date => ongoing
        self._add_role(
            proj,
            LeadProjectRoleTypes.PI,
            start_date=date.today() - timedelta(days=400),
            end_date=date.today() - timedelta(days=30),
        )
        rows = {r["name"]: r for r in get_check("project-leadership").get_rows()}
        self.assertIn("Stale Lead Project", rows)
        self.assertEqual(rows["Stale Lead Project"]["issues"], "no active PI")
        self.assertEqual(rows["Stale Lead Project"]["pi_count"], 1)
        self.assertEqual(rows["Stale Lead Project"]["active_pi_count"], 0)

    def test_project_with_active_pi_not_flagged(self):
        from datetime import date, timedelta
        from website.models.project_role import LeadProjectRoleTypes

        proj = self.make_project(name="Well-Led Project")
        self._add_role(
            proj,
            LeadProjectRoleTypes.PI,
            start_date=date.today() - timedelta(days=30),
        )
        names = {r["name"] for r in get_check("project-leadership").get_rows()}
        self.assertNotIn("Well-Led Project", names)

    def test_ended_project_with_ended_pi_not_flagged(self):
        from datetime import date, timedelta
        from website.models.project_role import LeadProjectRoleTypes

        proj = self.make_project(
            name="Wrapped-Up Project",
            end_date=date.today() - timedelta(days=10),
        )
        self._add_role(
            proj,
            LeadProjectRoleTypes.PI,
            start_date=date.today() - timedelta(days=400),
            end_date=date.today() - timedelta(days=20),
        )
        names = {r["name"] for r in get_check("project-leadership").get_rows()}
        self.assertNotIn("Wrapped-Up Project", names)


class PositionIntegrityCheckTests(DatabaseTestCase):
    def test_no_position_and_self_advisor(self):
        from datetime import date as _date

        from website.models import Position
        from website.models.position import Title

        p_nopos = self.make_person(first_name="No", last_name="Position")
        p_self = self.make_person(first_name="Self", last_name="Advisor")
        Position.objects.create(
            person=p_self,
            start_date=_date(2020, 1, 1),
            title=Title.PHD_STUDENT,
            advisor=p_self,
        )
        issues = {
            (r["person_id"], r["issue"])
            for r in get_check("position-integrity").get_rows()
        }
        self.assertIn((p_nopos.pk, "no position"), issues)
        self.assertIn((p_self.pk, "self-advisor"), issues)


class NewsHealthCheckTests(DatabaseTestCase):
    def test_flags_missing_slug_and_author(self):
        from website.models import News

        author = self.make_person(first_name="News", last_name="Writer")
        n_noauthor = self.make_news_item(title="Orphan News", author=None)
        n_noslug = self.make_news_item(title="Slugless News", author=author)
        News.objects.filter(pk=n_noslug.pk).update(slug="")  # save() auto-slugs

        rows = {r["id"]: r for r in get_check("news-health").get_rows()}
        self.assertIn(n_noauthor.pk, rows)
        self.assertFalse(rows[n_noauthor.pk]["has_author"])
        self.assertIn(n_noslug.pk, rows)
        self.assertTrue(rows[n_noslug.pk]["missing_slug"])


class MediaIntegrityCheckTests(DatabaseTestCase):
    def setUp(self):
        # Use a throwaway MEDIA_ROOT so the test never pollutes dev media.
        self._media_dir = tempfile.mkdtemp(prefix="dh_media_")
        self._override = override_settings(MEDIA_ROOT=self._media_dir)
        self._override.enable()
        self.addCleanup(self._override.disable)
        self.addCleanup(shutil.rmtree, self._media_dir, ignore_errors=True)

    def test_flags_missing_file(self):
        pub = self.make_publication(title="Vanishing Paper")
        path = pub.pdf_file.path
        if os.path.exists(path):
            os.remove(path)  # simulate a file that disappeared from disk
        hits = [
            r
            for r in get_check("media-integrity").get_rows()
            if r["type"] == "Publication"
            and r["id"] == pub.pk
            and r["status"] == "missing-file"
        ]
        self.assertTrue(hits)

    def test_missing_file_row_links_to_admin_edit(self):
        """A missing-file row gets an 'Open →' action to the artifact's admin
        edit page; orphan-file rows (no DB object) get no link."""
        pub = self.make_publication(title="Vanishing Paper")
        path = pub.pdf_file.path
        if os.path.exists(path):
            os.remove(path)

        check = get_check("media-integrity")
        missing = next(
            r
            for r in check.get_rows()
            if r["type"] == "Publication"
            and r["id"] == pub.pk
            and r["status"] == "missing-file"
        )
        label, url = check.row_link(missing)
        self.assertEqual(label, "Open →")
        self.assertEqual(
            url, reverse("admin:website_publication_change", args=[pub.pk])
        )

        # Orphan-file rows carry no id and must not produce a link.
        self.assertIsNone(
            check.row_link({"type": "Publication", "id": "", "status": "orphan-file"})
        )


class ActionLinkStandardizationTests(SimpleTestCase):
    """Every registered check must give its rows an action link (issue #1405),
    keeping admins one click from the fix. A check qualifies by either declaring
    ``link_model`` (default deep-link to the object's admin change page) or
    overriding ``row_link`` (custom target). This pins the standardization so a
    future check can't silently ship without one."""

    def test_every_check_provides_an_action_link(self):
        offenders = [
            c.slug for c in REGISTRY
            if c.link_model is None
            and type(c).row_link is HealthCheck.row_link
        ]
        self.assertEqual(
            offenders, [], f"checks lacking a per-row action link: {offenders}"
        )


class CompanionArtifactCheckTests(DatabaseTestCase):
    """Conference-paper-needs-talk and poster-needs-poster checks (issue #1405)."""

    def test_conference_paper_without_talk_is_flagged_and_linked(self):
        # make_publication defaults to a post-lab Conference paper with no talk.
        pub = self.make_publication(title="Talkless Conference Paper")
        check = get_check("conference-papers-without-talk")
        rows = {r["id"]: r for r in check.get_rows()}
        self.assertIn(pub.pk, rows)
        label, url = check.row_link(rows[pub.pk])
        self.assertEqual(label, "Open →")
        self.assertEqual(
            url, reverse("admin:website_publication_change", args=[pub.pk])
        )

    def test_conference_paper_with_talk_not_flagged(self):
        talk = self.make_talk(title="The Talk")
        pub = self.make_publication(title="Conference Paper With Talk", talk=talk)
        ids = [r["id"] for r in get_check("conference-papers-without-talk").get_rows()]
        self.assertNotIn(pub.pk, ids)

    def test_extended_abstract_conference_paper_not_flagged(self):
        pub = self.make_publication(
            title="Short-form Conference Paper", extended_abstract=True
        )
        ids = [r["id"] for r in get_check("conference-papers-without-talk").get_rows()]
        self.assertNotIn(pub.pk, ids)

    def test_to_appear_conference_paper_not_flagged(self):
        from datetime import date, timedelta

        future = date.today() + timedelta(days=365)
        pub = self.make_publication(title="Not Yet Presented", date=future)
        ids = [r["id"] for r in get_check("conference-papers-without-talk").get_rows()]
        self.assertNotIn(pub.pk, ids)

    def test_prelab_conference_paper_not_flagged(self):
        pub = self.make_publication(title="Grad School Paper", year=2010)
        ids = [r["id"] for r in get_check("conference-papers-without-talk").get_rows()]
        self.assertNotIn(pub.pk, ids)

    def test_poster_publication_without_poster_is_flagged(self):
        from website.models.publication import PubType

        pub = self.make_publication(
            title="Poster Pub, No Poster", pub_venue_type=PubType.POSTER
        )
        rows = {r["id"]: r for r in get_check("poster-papers-without-poster").get_rows()}
        self.assertIn(pub.pk, rows)
        # A poster-type pub must NOT be flagged by the talk check, and vice versa.
        talk_ids = [r["id"] for r in get_check("conference-papers-without-talk").get_rows()]
        self.assertNotIn(pub.pk, talk_ids)

    def test_poster_publication_with_poster_not_flagged(self):
        from website.models.publication import PubType
        from website.tests.factories import PosterFactory

        poster = PosterFactory(title="The Poster")
        pub = self.make_publication(
            title="Poster Pub With Poster",
            pub_venue_type=PubType.POSTER,
            poster=poster,
        )
        ids = [r["id"] for r in get_check("poster-papers-without-poster").get_rows()]
        self.assertNotIn(pub.pk, ids)


class DataHealthReadOnlyTests(DatabaseTestCase):
    def test_get_rows_does_not_mutate_db(self):
        from website.models import Person, Publication

        self.make_person(first_name="Jane", last_name="Doe")
        self.make_person(first_name="Jane", last_name="Doe")
        before = (Person.objects.count(), Publication.objects.count())
        for slug in (
            "duplicate-people", "url-name-collisions", "position-integrity",
            "project-leadership", "conference-papers-without-talk",
            "poster-papers-without-poster",
        ):
            get_check(slug).get_rows()
        after = (Person.objects.count(), Publication.objects.count())
        self.assertEqual(before, after)
