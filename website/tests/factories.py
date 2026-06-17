"""
factory_boy fixtures for the Makeability Lab models (#1272).

These factories are the single source of truth for building model instances in
tests. The ``DatabaseTestCase.make_*`` helpers in :mod:`website.tests.base`
delegate to them, so all existing DB-backed tests run through this code too.

Design notes
------------
- **Filesystem-light by default.** Image and PDF fields are populated with tiny
  in-memory uploads (a 1x1 GIF, a stub PDF) rather than real media. This matches
  the original ``base.py`` philosophy: the DB suite stays fast and never touches
  ``media/``. In particular, pre-setting ``Person.image`` / ``easter_egg`` skips
  ``Person.save()``'s Star Wars fallback, which would otherwise read a real file
  off disk. A later PR (#1272 layer 2) can add curated ``seed_media/`` files and
  point a seed-data command at them when real thumbnail/crop/PDF code paths
  actually need exercising.
- **No auto-authors.** ``PublicationFactory`` / ``TalkFactory`` / ``PosterFactory``
  do *not* invent authors. Callers pass ``authors=[...]`` (a list of ``Person``
  instances) when they want them; otherwise the artifact is created authorless.
  This keeps the ~200 existing ``make_publication`` call sites green (they add
  authors explicitly) and leaves authorless code paths testable. A seed-data
  command can pass ``authors=PersonFactory.create_batch(n)`` for a populated graph.

Usage
-----
    from website.tests.factories import PersonFactory, PublicationFactory

    alice = PersonFactory(first_name="Alice", last_name="Ng")
    pub = PublicationFactory(title="A Paper", authors=[alice])
    batch = PersonFactory.create_batch(5)   # five people with Faker names
"""

from datetime import date

import factory
from django.core.files.uploadedfile import SimpleUploadedFile

from website.models import (
    Award,
    News,
    Person,
    Poster,
    Project,
    ProjectRole,
    Publication,
    Talk,
    Video,
)
from website.models.award import AwardType
from website.models.publication import PubType
from website.models.talk import TalkType

# Smallest possible valid GIF (1x1, transparent). Used for ImageFields so the
# upload validators (extension + magic-byte header) pass without reading disk.
_GIF_1PX = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00"
    b"!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01"
    b"\x00\x00\x02\x02D\x01\x00;"
)

# Minimal stub with a real %PDF magic header so validate_pdf_upload passes.
_PDF_STUB = b"%PDF-1.4 test"


def image_upload(name):
    """Return a SimpleUploadedFile satisfying an ImageField (1x1 GIF)."""
    return SimpleUploadedFile(name, _GIF_1PX, content_type="image/gif")


def pdf_upload(name):
    """Return a SimpleUploadedFile satisfying a pdf_file FileField."""
    return SimpleUploadedFile(name, _PDF_STUB, content_type="application/pdf")


class PersonFactory(factory.django.DjangoModelFactory):
    """A Person with both image fields pre-set (skips the Star Wars fallback)."""

    class Meta:
        model = Person

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    image = factory.LazyAttribute(
        lambda o: image_upload(f"{o.first_name}_{o.last_name}.gif")
    )
    easter_egg = factory.LazyAttribute(
        lambda o: image_upload(f"{o.first_name}_{o.last_name}_egg.gif")
    )


class ProjectFactory(factory.django.DjangoModelFactory):
    """
    A Project. Created exactly as Project.save() leaves it, i.e.
    ``is_visible=False`` (private) unless you pass ``is_visible=True``.
    ``short_name`` is derived from ``name`` (lowercased, no spaces) plus a
    sequence suffix so factory-built projects get distinct URL slugs.
    """

    class Meta:
        model = Project

    name = factory.Faker("catch_phrase")
    short_name = factory.Sequence(lambda n: f"project{n}")


class VideoFactory(factory.django.DjangoModelFactory):
    """
    A Video. ``video_url`` defaults to a real YouTube URL because
    ``Video.get_video_host_str()`` substring-matches it (a None url would raise)
    and the video snippet embeds it.
    """

    class Meta:
        model = Video

    title = factory.Faker("sentence", nb_words=5)
    date = factory.Faker("date_between", start_date="-3y", end_date="today")
    video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


class _ArtifactFactory(factory.django.DjangoModelFactory):
    """
    Shared declarations for the Artifact subclasses (Publication/Talk/Poster).
    Abstract: not a model itself, just a mixin of common fields plus the
    ``authors`` post-generation hook.
    """

    class Meta:
        abstract = True

    title = factory.Faker("sentence", nb_words=8)
    date = factory.Faker("date_between", start_date="-3y", end_date="today")
    forum_name = "CHI"
    pdf_file = factory.LazyAttribute(
        lambda o: pdf_upload(f"{o.title.replace(' ', '_')[:40]}.pdf")
    )

    @factory.post_generation
    def authors(self, create, extracted, **kwargs):
        """Set authors only when explicitly provided (see module docstring)."""
        if create and extracted:
            self.authors.set(extracted)


class PublicationFactory(_ArtifactFactory):
    """A Publication (defaults to a peer-reviewed conference paper)."""

    class Meta:
        model = Publication

    pub_venue_type = PubType.CONFERENCE


class TalkFactory(_ArtifactFactory):
    """A Talk. Artifact.save() generates a thumbnail from pdf_file on save."""

    class Meta:
        model = Talk

    talk_type = TalkType.CONFERENCE_TALK


class PosterFactory(_ArtifactFactory):
    """A Poster."""

    class Meta:
        model = Poster


class NewsItemFactory(factory.django.DjangoModelFactory):
    """
    A News item. ``author`` is intentionally left null by default (the FK is
    nullable, on_delete=SET_NULL) so the authorless code path stays exercised;
    pass ``author=PersonFactory()`` for an authored item.
    """

    class Meta:
        model = News

    title = factory.Faker("sentence", nb_words=6)
    date = factory.Faker("date_between", start_date="-3y", end_date="today")
    content = factory.Faker("paragraph")


class AwardFactory(factory.django.DjangoModelFactory):
    """
    An external Award (the Awards-page kind, distinct from Publication.award).
    Pass ``recipients=[person, ...]`` and/or ``projects=[...]`` to link them.
    """

    class Meta:
        model = Award

    title = factory.Faker("sentence", nb_words=5)
    date = factory.Faker("date_between", start_date="-3y", end_date="today")
    award_type = AwardType.STUDENT_AWARD

    @factory.post_generation
    def recipients(self, create, extracted, **kwargs):
        if create and extracted:
            self.recipients.set(extracted)


class ProjectRoleFactory(factory.django.DjangoModelFactory):
    """
    A ProjectRole linking a Person to a Project. Builds its own Person and
    Project via SubFactory unless you pass ``person=`` / ``project=``.
    ``start_date`` is required by the model, so it always gets a value.
    """

    class Meta:
        model = ProjectRole

    person = factory.SubFactory(PersonFactory)
    project = factory.SubFactory(ProjectFactory)
    start_date = factory.Faker("date_between", start_date="-3y", end_date="today")
