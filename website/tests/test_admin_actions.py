"""
Phase 4 of the admin changelist audit (#1346): workflow niceties —
list_editable toggles, bulk actions, and Keyword cleanup tooling.

Covers:
  - ProjectAdmin: inline is_visible toggle config + make_public/make_private actions.
  - PublicationAdmin: export-as-BibTeX download + mark/unmark peer-reviewed actions.
  - KeywordAdmin: total_usage counts every referencing model (so the "Unused"
    filter doesn't flag a keyword that's only used by, e.g., a Talk).
"""

from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.http import HttpResponse
from django.test import RequestFactory

from website.models import (Project, Publication, Keyword)
from website.admin.admin_site import ml_admin_site
from website.admin.project_admin import ProjectAdmin
from website.admin.publication_admin import PublicationAdmin
from website.admin.keyword_admin import KeywordAdmin
from website.tests.factories import (PersonFactory, ProjectFactory,
                                     PublicationFactory, TalkFactory)
from website.tests.base import DatabaseTestCase


class _ActionTestBase(DatabaseTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = get_user_model().objects.create_superuser(
            username="actionadmin", email="a@example.com", password="x")

    def setUp(self):
        self.rf = RequestFactory()

    def _request(self):
        """A POST request with a message store attached (admin actions that call
        message_user need one)."""
        request = self.rf.post('/')
        request.user = self.superuser
        request.session = {}
        setattr(request, '_messages', FallbackStorage(request))
        return request


class ProjectActionTests(_ActionTestBase):
    def setUp(self):
        super().setUp()
        self.admin = ProjectAdmin(Project, ml_admin_site)

    def test_is_visible_is_inline_editable(self):
        self.assertIn('is_visible', self.admin.list_editable)
        # list_editable fields must not be the row link column.
        self.assertEqual(self.admin.list_display[0], 'name')

    def test_make_public_and_private(self):
        p1 = ProjectFactory(is_visible=False)
        p2 = ProjectFactory(is_visible=False)
        self.admin.make_public(self._request(), Project.objects.filter(pk__in=[p1.pk, p2.pk]))
        self.assertTrue(Project.objects.get(pk=p1.pk).is_visible)
        self.assertTrue(Project.objects.get(pk=p2.pk).is_visible)

        self.admin.make_private(self._request(), Project.objects.filter(pk=p1.pk))
        self.assertFalse(Project.objects.get(pk=p1.pk).is_visible)
        self.assertTrue(Project.objects.get(pk=p2.pk).is_visible)  # unaffected


class PublicationActionTests(_ActionTestBase):
    def setUp(self):
        super().setUp()
        self.admin = PublicationAdmin(Publication, ml_admin_site)

    def test_export_as_bibtex_downloads_bib_file(self):
        pub = PublicationFactory(title="A Study of Things",
                                 authors=[PersonFactory(last_name="Ng")])
        response = self.admin.export_as_bibtex(
            self._request(), Publication.objects.filter(pk=pub.pk))
        self.assertIsInstance(response, HttpResponse)
        self.assertIn('bibtex', response['Content-Type'])
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertIn('.bib', response['Content-Disposition'])
        body = response.content.decode()
        self.assertIn('@inproceedings', body)   # CONFERENCE venue type
        self.assertIn('author=', body)

    def test_mark_and_unmark_peer_reviewed(self):
        pub = PublicationFactory(peer_reviewed=None)
        self.admin.mark_peer_reviewed(self._request(), Publication.objects.filter(pk=pub.pk))
        self.assertIs(Publication.objects.get(pk=pub.pk).peer_reviewed, True)
        self.admin.unmark_peer_reviewed(self._request(), Publication.objects.filter(pk=pub.pk))
        self.assertIs(Publication.objects.get(pk=pub.pk).peer_reviewed, False)


class KeywordUsageTests(_ActionTestBase):
    def setUp(self):
        super().setUp()
        self.admin = KeywordAdmin(Keyword, ml_admin_site)

    def _annotated(self, keyword):
        return self.admin.get_queryset(self._request()).get(pk=keyword.pk)

    def test_total_usage_counts_all_referencing_models(self):
        kw = Keyword.objects.create(keyword="ubicomp")
        PublicationFactory().keywords.add(kw)
        TalkFactory().keywords.add(kw)
        ProjectFactory().keywords.add(kw)
        ann = self._annotated(kw)
        self.assertEqual(self.admin.total_usage(ann), 3)
        self.assertEqual(self.admin.publication_count(ann), 1)
        self.assertEqual(self.admin.project_count(ann), 1)

    def test_talk_only_keyword_is_not_unused(self):
        """The whole point of broadening the count: a keyword used only by a Talk
        shows project_count=0 and publication_count=0 but must NOT be 'Unused'."""
        kw = Keyword.objects.create(keyword="speech")
        TalkFactory().keywords.add(kw)
        ann = self._annotated(kw)
        self.assertEqual(self.admin.project_count(ann), 0)
        self.assertEqual(self.admin.publication_count(ann), 0)
        self.assertEqual(self.admin.total_usage(ann), 1)
        # The "Unused" predicate (_total_usage=0) must not match it.
        unused_pks = self.admin.get_queryset(self._request()).filter(
            _total_usage=0).values_list('pk', flat=True)
        self.assertNotIn(kw.pk, list(unused_pks))

    def test_orphan_keyword_is_unused(self):
        kw = Keyword.objects.create(keyword="orphan")
        unused_pks = list(self.admin.get_queryset(self._request()).filter(
            _total_usage=0).values_list('pk', flat=True))
        self.assertIn(kw.pk, unused_pks)
