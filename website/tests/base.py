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

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase


# Minimal 1x1 GIF used to satisfy Person.image / Person.easter_egg without
# touching the filesystem. Person.save() picks a random Star Wars image when
# either field is empty, opening a real file from media/. Pre-setting both
# with this SimpleUploadedFile skips the fallback branch entirely.
_GIF_1PX = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00"
    b"!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01"
    b"\x00\x00\x02\x02D\x01\x00;"
)


def _make_image_upload(name):
    """Return a SimpleUploadedFile that satisfies an ImageField."""
    return SimpleUploadedFile(name, _GIF_1PX, content_type="image/gif")


class DatabaseTestCase(TestCase):
    """
    Shared base for tests that touch the database. Provides small fixture
    helpers (make_person / make_publication / make_news_item) built on
    plain Model.objects.create() — no third-party fixture library. Each
    test runs inside a transaction and is rolled back, so tests stay
    isolated without manual cleanup.

    Why a base class instead of module-level helpers: subclasses can
    override the defaults in setUp() and the helpers can grow without
    cluttering the module namespace.
    """

    def make_person(self, first_name="Jane", last_name="Doe", **kwargs):
        """
        Create and return a Person. Image fields are pre-populated to
        skip Person.save()'s Star Wars fallback (which reads a real file
        from media/). Override by passing image=... explicitly.
        """
        from website.models import Person
        kwargs.setdefault(
            "image", _make_image_upload(f"{first_name}_{last_name}.gif")
        )
        kwargs.setdefault(
            "easter_egg",
            _make_image_upload(f"{first_name}_{last_name}_egg.gif"),
        )
        return Person.objects.create(
            first_name=first_name, last_name=last_name, **kwargs
        )

    def make_publication(self, title="A Test Paper", year=2024, **kwargs):
        """
        Create and return a Publication with sensible defaults: post-lab-
        formation date, conference venue, a forum name, and a dummy PDF
        (display_pub_snippet.html unconditionally renders pub.pdf_file.url,
        so tests that go through the publications view need one to render).
        Override via kwargs.
        """
        from datetime import date as _date
        from website.models import Publication
        from website.models.publication import PubType
        kwargs.setdefault("date", _date(year, 1, 1))
        kwargs.setdefault("forum_name", "CHI")
        kwargs.setdefault("pub_venue_type", PubType.CONFERENCE)
        kwargs.setdefault(
            "pdf_file",
            SimpleUploadedFile(
                f"{title.replace(' ', '_')}.pdf",
                b"%PDF-1.4 test",
                content_type="application/pdf",
            ),
        )
        return Publication.objects.create(title=title, **kwargs)

    def make_talk(self, title="A Test Talk", year=2024, **kwargs):
        """
        Create and return a Talk. Artifact.save() generates a thumbnail
        from pdf_file (via ImageMagick) on every save, so we provide a
        small valid PDF and let it run; tests that don't care about the
        thumbnail just ignore it.
        """
        from datetime import date as _date
        from website.models import Talk
        from website.models.talk import TalkType
        kwargs.setdefault("date", _date(year, 1, 1))
        kwargs.setdefault("forum_name", "CHI")
        kwargs.setdefault("talk_type", TalkType.CONFERENCE_TALK)
        kwargs.setdefault(
            "pdf_file",
            SimpleUploadedFile(
                f"{title.replace(' ', '_')}.pdf",
                b"%PDF-1.4 test",
                content_type="application/pdf",
            ),
        )
        return Talk.objects.create(title=title, **kwargs)

    def make_news_item(self, title="Test News", author=None, **kwargs):
        """
        Create and return a News item. `author` is intentionally optional
        (the FK is nullable with on_delete=SET_NULL) so tests can exercise
        the authorless code path that caused the original /news/158/ bug.
        """
        from datetime import date as _date
        from website.models import News
        kwargs.setdefault("date", _date(2024, 1, 1))
        kwargs.setdefault("content", "Test news body.")
        return News.objects.create(title=title, author=author, **kwargs)
