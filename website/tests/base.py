"""
Shared database-backed test infrastructure (#1267).

Tests built on :class:`DatabaseTestCase` use Django's ``TestCase``, which wraps
each test in a transaction that's rolled back at the end. They exercise real
model code, real querysets, and the URL/view/template layer.

Why this exists: several 2.3.4 fixes (publications prefetch_related, news
null-author guards, delete_unused_files .path guards) shipped without
regression tests because the bugs were only reachable through a real queryset
or view. This base class establishes the foundation for backfilling that
coverage incrementally. See #1267 for the broader plan.
"""

from datetime import date as _date

from django.test import TestCase

from website.tests.factories import (
    NewsItemFactory,
    PersonFactory,
    ProjectFactory,
    PublicationFactory,
    TalkFactory,
    VideoFactory,
    image_upload,
)


class DatabaseTestCase(TestCase):
    """
    Shared base for tests that touch the database. Provides small fixture
    helpers (make_person / make_publication / make_news_item / ...) that
    delegate to the factory_boy factories in :mod:`website.tests.factories`
    (#1272). The factories are the single source of truth for building
    instances; these helpers preserve the original keyword API (notably the
    ``year`` shorthand) so the existing suite keeps working unchanged. Each
    test runs inside a transaction and is rolled back, so tests stay isolated
    without manual cleanup.

    Why keep the helpers at all: they encode test-friendly defaults (fixed
    dates via ``year``, ``with_thumbnail`` for the project visibility backfill)
    and give subclasses a stable seam to override in ``setUp()``. Tests that
    want richer fixtures (Faker values, batches, the relationship graph) can
    import and use the factories directly.
    """

    def make_person(self, first_name="Jane", last_name="Doe", **kwargs):
        """
        Create and return a Person. Image fields are pre-populated by
        PersonFactory to skip Person.save()'s Star Wars fallback (which reads a
        real file from media/). Override by passing image=... explicitly.
        """
        return PersonFactory(
            first_name=first_name, last_name=last_name, **kwargs
        )

    def make_publication(self, title="A Test Paper", year=2024, **kwargs):
        """
        Create and return a Publication with sensible defaults: post-lab-
        formation date (from ``year``), conference venue, a forum name, and a
        dummy PDF (display_pub_snippet.html unconditionally renders
        pub.pdf_file.url, so tests that go through the publications view need
        one to render). Override via kwargs.
        """
        kwargs.setdefault("date", _date(year, 1, 1))
        return PublicationFactory(title=title, **kwargs)

    def make_talk(self, title="A Test Talk", year=2024, **kwargs):
        """
        Create and return a Talk. Artifact.save() generates a thumbnail
        from pdf_file (via ImageMagick) on every save, so the factory provides
        a small valid PDF and lets it run; tests that don't care about the
        thumbnail just ignore it.
        """
        kwargs.setdefault("date", _date(year, 1, 1))
        return TalkFactory(title=title, **kwargs)

    def make_video(self, title="A Test Video", year=2024, **kwargs):
        """
        Create and return a Video. video_url defaults to a YouTube URL because
        Video.get_video_host_str() does a substring check on it (a None url
        would raise), and the video snippet embeds it. date is set so
        get_most_recent_artifact_date() has something to sort on.
        """
        kwargs.setdefault("date", _date(year, 1, 1))
        return VideoFactory(title=title, **kwargs)

    def make_news_item(self, title="Test News", author=None, **kwargs):
        """
        Create and return a News item. `author` is intentionally optional
        (the FK is nullable with on_delete=SET_NULL) so tests can exercise
        the authorless code path that caused the original /news/158/ bug.
        """
        kwargs.setdefault("date", _date(2024, 1, 1))
        kwargs.setdefault("content", "Test news body.")
        return NewsItemFactory(title=title, author=author, **kwargs)

    def make_project(self, name="A Test Project", short_name=None,
                     with_thumbnail=False, **kwargs):
        """
        Create and return a Project. By default the project is created exactly
        as Project.save() leaves it (is_visible=False, i.e. private), so tests
        that care about visibility should pass is_visible=True explicitly or
        flip it afterwards.

        Args:
            with_thumbnail: when True, attaches a small valid gallery_image so
                tests can exercise the legacy thumbnail criterion used by the
                visibility backfill. Defaults to False to avoid touching the
                filesystem unnecessarily.
        """
        if short_name is None:
            short_name = name.lower().replace(" ", "")
        if with_thumbnail:
            kwargs.setdefault(
                "gallery_image",
                image_upload(f"{short_name}_thumb.gif"),
            )
        return ProjectFactory(name=name, short_name=short_name, **kwargs)
