"""
Phase 3 of the admin changelist audit (#1346): prefetch the artifact-family
changelists so their per-row callable columns (author/speaker lists, sponsor,
recipients, projects) stop issuing per-row queries.

Coverage mirrors Phase 2:
  1. Correctness — the rewritten ``Artifact.get_first_author_last_name`` (now
     reads ``list(self.authors.all())`` so a prefetch resolves it) and the
     rewritten ``PublicationAdmin.display_authors`` are behavior-preserving.
  2. Regression — each changelist's steady-state query count stays flat as rows
     grow (3 -> 6). Before this phase, columns like ``display_authors`` (a
     ``[:5]`` slice + ``.count()``) or ``get_speakers_as_csv`` fired 1-3 queries
     per row.
"""

from website.models import Publication, Poster
from website.admin.admin_site import ml_admin_site
from website.admin.publication_admin import PublicationAdmin
from website.admin.talk_admin import TalkAdmin
from website.admin.poster_admin import PosterAdmin
from website.admin.video_admin import VideoAdmin
from website.admin.award_admin import AwardAdmin
from website.tests.factories import (PersonFactory, ProjectFactory,
                                     PublicationFactory, TalkFactory,
                                     PosterFactory, VideoFactory, AwardFactory)
from website.tests.test_admin_perf import _AdminPerfBase
from website.tests.base import DatabaseTestCase


class ArtifactFirstAuthorTests(DatabaseTestCase):
    """get_first_author_last_name (rewritten to use list(self.authors.all()))."""

    def test_returns_first_author_in_sorted_order(self):
        first = PersonFactory(last_name="Aaa")
        second = PersonFactory(last_name="Bbb")
        poster = PosterFactory(authors=[first, second])
        self.assertEqual(poster.get_first_author_last_name(), "Aaa")

    def test_unknown_when_no_authors(self):
        poster = PosterFactory()
        self.assertEqual(poster.get_first_author_last_name(), "Unknown")


class PublicationDisplayAuthorsTests(DatabaseTestCase):
    """PublicationAdmin.display_authors caps at five names and appends an ellipsis."""

    def setUp(self):
        self.admin = PublicationAdmin(Publication, ml_admin_site)

    def test_six_authors_shows_five_plus_ellipsis(self):
        people = [PersonFactory(first_name=f"A{i}", last_name=f"L{i}") for i in range(6)]
        pub = PublicationFactory(authors=people)
        rendered = self.admin.display_authors(pub)
        self.assertIn("...", rendered)
        self.assertEqual(rendered.count(","), 5)  # 5 names + "..." => 5 commas

    def test_no_authors(self):
        pub = PublicationFactory()
        self.assertEqual(self.admin.display_authors(pub), "No authors")


class ArtifactChangelistPerfTests(_AdminPerfBase):
    """Each artifact changelist's query count stays flat as rows grow (3 -> 6)."""

    def _assert_flat(self, model_admin, params, make_fn):
        make_fn(0, 3)
        n1 = self._steady_state_query_count(model_admin, params)
        make_fn(3, 6)
        n2 = self._steady_state_query_count(model_admin, params)
        self.assertEqual(
            n1, n2,
            f"{type(model_admin).__name__} N+1: {n1} -> {n2} queries as rows grew 3 -> 6")

    def test_publications_flat(self):
        def make(start, end):
            for i in range(start, end):
                pub = PublicationFactory(
                    title=f"Pub {i}",
                    authors=[PersonFactory(), PersonFactory()])
                pub.projects.set([ProjectFactory()])
        self._assert_flat(PublicationAdmin(Publication, ml_admin_site), {}, make)

    def test_talks_flat(self):
        from website.models import Talk
        def make(start, end):
            for i in range(start, end):
                TalkFactory(title=f"Talk {i}",
                            authors=[PersonFactory(), PersonFactory()])
        self._assert_flat(TalkAdmin(Talk, ml_admin_site), {}, make)

    def test_posters_flat(self):
        def make(start, end):
            for i in range(start, end):
                PosterFactory(title=f"Poster {i}",
                              authors=[PersonFactory(), PersonFactory()])
        self._assert_flat(PosterAdmin(Poster, ml_admin_site), {}, make)

    def test_videos_flat(self):
        from website.models import Video
        def make(start, end):
            for i in range(start, end):
                video = VideoFactory(title=f"Video {i}")
                video.projects.set([ProjectFactory(), ProjectFactory()])
        self._assert_flat(VideoAdmin(Video, ml_admin_site), {}, make)

    def test_awards_flat(self):
        from website.models import Award
        def make(start, end):
            for i in range(start, end):
                award = AwardFactory(title=f"Award {i}",
                                     recipients=[PersonFactory(), PersonFactory()])
                award.projects.set([ProjectFactory()])
        self._assert_flat(AwardAdmin(Award, ml_admin_site), {}, make)
