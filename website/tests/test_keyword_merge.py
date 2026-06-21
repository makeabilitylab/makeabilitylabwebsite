"""
Tests for the destructive "Merge selected keywords" admin action and the
duplicate-keywords data-health check (#1352).

Coverage:
  * merge reassigns references across all six keyword-holding models, then
    deletes the merged-away keywords;
  * an object already tagged with the target gains no duplicate M2M row;
  * a keyword passed as both source and target is skipped (no self-delete);
  * the admin action is a no-op when fewer than two keywords are selected;
  * the data-health check clusters case/whitespace variants and ignores
    singletons.
"""

from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.db import connection
from django.test import RequestFactory
from django.urls import reverse

from website.models import (Keyword, Publication, Talk, Poster, Grant,
                            Project, ProjectUmbrella, Sponsor)
from website.admin.admin_site import ml_admin_site
from website.admin.keyword_admin import KeywordAdmin, merge_keywords_into_target
from website.admin.data_health.checks.duplicate_keywords import DuplicateKeywordsCheck
from website.tests.base import DatabaseTestCase


class KeywordMergeHelperTests(DatabaseTestCase):
    """Exercise the reusable merge function directly (no request plumbing)."""

    def _tag_one_object_per_model(self, keyword):
        """Create one object of each of the six keyword-holding models, tag each
        with ``keyword``, and return them so callers can assert reassignment."""
        sponsor = Sponsor.objects.create(name="NSF")
        objects = {
            'publication': self.make_publication(title="P"),
            'talk': self.make_talk(title="T"),
            'poster': Poster.objects.create(title="Po", date=date(2024, 1, 1),
                                            forum_name="CHI"),
            'project': self.make_project(name="Proj"),
            'project_umbrella': ProjectUmbrella.objects.create(
                name="Umb", short_name="umb"),
            'grant': Grant.objects.create(title="G", date=date(2024, 1, 1),
                                          forum_name="NSF", sponsor=sponsor),
        }
        for obj in objects.values():
            obj.keywords.add(keyword)
        return objects

    def test_merge_reassigns_all_six_relations_and_deletes_source(self):
        target = Keyword.objects.create(keyword="Speech")
        source = Keyword.objects.create(keyword="speech")
        objects = self._tag_one_object_per_model(source)

        removed = merge_keywords_into_target(target, [source])

        self.assertEqual(removed, 1)
        self.assertFalse(Keyword.objects.filter(pk=source.pk).exists())
        for name, obj in objects.items():
            keyword_ids = list(obj.keywords.values_list('pk', flat=True))
            self.assertEqual(keyword_ids, [target.pk],
                             f"{name} should now reference only the target keyword")

    def test_object_already_tagged_with_target_has_no_duplicate(self):
        target = Keyword.objects.create(keyword="HCI")
        source = Keyword.objects.create(keyword="hci")
        pub = self.make_publication(title="Already tagged")
        pub.keywords.add(target, source)  # tagged with BOTH

        merge_keywords_into_target(target, [source])

        # add() is idempotent, so the target appears exactly once — not twice.
        self.assertEqual(list(pub.keywords.values_list('pk', flat=True)),
                         [target.pk])
        self.assertFalse(Keyword.objects.filter(pk=source.pk).exists())

    def test_object_tagged_with_two_sources_at_once(self):
        target = Keyword.objects.create(keyword="Design")
        source_a = Keyword.objects.create(keyword="design")
        source_b = Keyword.objects.create(keyword="DESIGN")
        pub = self.make_publication(title="Double tagged")
        pub.keywords.add(source_a, source_b)  # tagged with BOTH sources, not target

        merge_keywords_into_target(target, [source_a, source_b])

        # Both sources collapse to a single target row, not a duplicate pair.
        self.assertEqual(list(pub.keywords.values_list('pk', flat=True)),
                         [target.pk])
        self.assertEqual(Keyword.objects.filter(
            pk__in=[source_a.pk, source_b.pk]).count(), 0)

    def test_merge_survives_legacy_sort_value_column(self):
        """Reproduces the -test/prod failure: the deployed keywords through table
        carries a leftover NOT-NULL ``sort_value`` column (the field used to be a
        SortedManyToManyField). Inserting a new through row via .add() violates
        the constraint; the merge must repoint existing rows instead.

        settings_test builds the schema from the current (plain M2M) models, so
        the column isn't there by default — we add it here to mimic the deployed
        drift, then assert the merge still succeeds.
        """
        target = Keyword.objects.create(keyword="Design Process")
        source = Keyword.objects.create(keyword="design process")
        pub = self.make_publication(title="Legacy schema paper")
        pub.keywords.add(source)  # inserted before the column exists — fine

        table = Publication.keywords.through._meta.db_table
        with connection.cursor() as cursor:
            # The .add() above left deferred FK trigger events pending, which
            # block ALTER TABLE; force them to resolve now so we can add the
            # column inside this test transaction.
            cursor.execute('SET CONSTRAINTS ALL IMMEDIATE')
            cursor.execute(f'ALTER TABLE {table} ADD COLUMN sort_value integer')
            cursor.execute(f'UPDATE {table} SET sort_value = 0')
            cursor.execute(
                f'ALTER TABLE {table} ALTER COLUMN sort_value SET NOT NULL')

        # Must not raise IntegrityError on the NOT-NULL sort_value column.
        merge_keywords_into_target(target, [source])

        self.assertEqual(list(pub.keywords.values_list('pk', flat=True)),
                         [target.pk])
        self.assertFalse(Keyword.objects.filter(pk=source.pk).exists())

    def test_target_in_sources_is_skipped(self):
        target = Keyword.objects.create(keyword="Robotics")
        source = Keyword.objects.create(keyword="robotics")

        # Passing the target itself among the sources must not delete it.
        removed = merge_keywords_into_target(target, [target, source])

        self.assertEqual(removed, 1)
        self.assertTrue(Keyword.objects.filter(pk=target.pk).exists())
        self.assertFalse(Keyword.objects.filter(pk=source.pk).exists())


class KeywordMergeActionTests(DatabaseTestCase):
    """Exercise the admin action wrapper (selection guards + confirm path)."""

    def setUp(self):
        super().setUp()
        self.admin = KeywordAdmin(Keyword, ml_admin_site)
        self.factory = RequestFactory()

    def _request(self, data=None):
        request = self.factory.post('/admin/website/keyword/', data or {})
        request.user = None
        # Action handlers call message_user(), which needs a message store.
        setattr(request, 'session', {})
        setattr(request, '_messages', FallbackStorage(request))
        return request

    def test_single_selection_is_a_noop(self):
        only = Keyword.objects.create(keyword="solo")
        request = self._request()

        result = self.admin.merge_keywords(request, Keyword.objects.filter(pk=only.pk))

        self.assertIsNone(result)
        self.assertTrue(Keyword.objects.filter(pk=only.pk).exists())

    def test_confirm_post_merges_and_deletes(self):
        target = Keyword.objects.create(keyword="Speech")
        source = Keyword.objects.create(keyword="speech")
        pub = self.make_publication(title="Confirmed merge")
        pub.keywords.add(source)

        request = self._request({
            'confirm_merge': 'yes',
            'target': str(target.pk),
        })
        result = self.admin.merge_keywords(
            request, Keyword.objects.filter(pk__in=[target.pk, source.pk]))

        self.assertIsNone(result)  # returns to changelist
        self.assertFalse(Keyword.objects.filter(pk=source.pk).exists())
        self.assertEqual(list(pub.keywords.values_list('pk', flat=True)),
                         [target.pk])


class KeywordNormalizationTests(DatabaseTestCase):
    """Layer-1 ward: Keyword.save() normalizes whitespace (#1352)."""

    def test_save_trims_and_collapses_whitespace(self):
        kw = Keyword.objects.create(keyword="  Speech   recognition  ")
        kw.refresh_from_db()
        self.assertEqual(kw.keyword, "Speech recognition")

    def test_casing_is_preserved(self):
        # Whitespace is normalized, but casing is intentionally left alone so
        # acronyms like VR / HCI / iOS keep their intended form.
        kw = Keyword.objects.create(keyword="  HCI ")
        kw.refresh_from_db()
        self.assertEqual(kw.keyword, "HCI")


class DuplicateKeywordsCheckTests(DatabaseTestCase):
    """The finder must cluster case/whitespace variants and skip singletons."""

    def test_clusters_case_variants_and_ignores_unique_keywords(self):
        # Whitespace variants are now prevented at save (layer 1), so the
        # finder's remaining job is case variants, which still coexist until the
        # layer-2 case-insensitive constraint lands.
        Keyword.objects.create(keyword="Speech")
        Keyword.objects.create(keyword="speech")
        Keyword.objects.create(keyword="Robotics")  # unique → not flagged

        rows = DuplicateKeywordsCheck().get_rows()

        flagged = {r['keyword'] for r in rows}
        self.assertEqual(flagged, {"Speech", "speech"})
        # Both share one normalized cluster key.
        self.assertEqual({r['cluster_key'] for r in rows}, {"speech"})

    def test_total_uses_counts_references(self):
        kw_a = Keyword.objects.create(keyword="VR")
        Keyword.objects.create(keyword="vr")  # variant so the cluster qualifies
        pub = self.make_publication(title="VR paper")
        pub.keywords.add(kw_a)

        rows = {r['id']: r for r in DuplicateKeywordsCheck().get_rows()}

        self.assertEqual(rows[kw_a.pk]['publication_count'], 1)
        self.assertEqual(rows[kw_a.pk]['total_uses'], 1)

    def test_row_link_points_to_filtered_keyword_changelist(self):
        kw = Keyword.objects.create(keyword="Speech")
        Keyword.objects.create(keyword="speech")  # makes the cluster qualify

        rows = {r['id']: r for r in DuplicateKeywordsCheck().get_rows()}
        label, url = DuplicateKeywordsCheck().row_link(rows[kw.pk])

        self.assertIn('Merge', label)
        # Deep-links to the Keyword changelist filtered to the folded cluster key.
        self.assertIn('/admin/website/keyword/', url)
        self.assertIn('q=speech', url)

    def test_detail_page_renders_deep_link(self):
        # End-to-end: the data-health detail page renders the per-row "Merge in
        # admin" deep link (exercises the template's optional-link branch).
        Keyword.objects.create(keyword="Speech")
        Keyword.objects.create(keyword="speech")
        superuser = get_user_model().objects.create_superuser(
            username="dh_admin", email="a@b.co", password="pw")
        self.client.force_login(superuser)

        resp = self.client.get(
            reverse("admin:data_health_detail", args=["duplicate-keywords"]))

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "/admin/website/keyword/?q=speech")
        self.assertContains(resp, "Merge in admin")
