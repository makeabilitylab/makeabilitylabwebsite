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

from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory

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


class DuplicateKeywordsCheckTests(DatabaseTestCase):
    """The finder must cluster case/whitespace variants and skip singletons."""

    def test_clusters_variants_and_ignores_unique_keywords(self):
        Keyword.objects.create(keyword="Speech")
        Keyword.objects.create(keyword="speech")
        Keyword.objects.create(keyword="Speech ")   # trailing whitespace
        Keyword.objects.create(keyword="Robotics")  # unique → not flagged

        rows = DuplicateKeywordsCheck().get_rows()

        flagged = {r['keyword'] for r in rows}
        self.assertEqual(flagged, {"Speech", "speech", "Speech "})
        # All three share one normalized cluster key.
        self.assertEqual({r['cluster_key'] for r in rows}, {"speech"})

    def test_total_uses_counts_references(self):
        kw_a = Keyword.objects.create(keyword="VR")
        Keyword.objects.create(keyword="vr")  # variant so the cluster qualifies
        pub = self.make_publication(title="VR paper")
        pub.keywords.add(kw_a)

        rows = {r['id']: r for r in DuplicateKeywordsCheck().get_rows()}

        self.assertEqual(rows[kw_a.pk]['publication_count'], 1)
        self.assertEqual(rows[kw_a.pk]['total_uses'], 1)
