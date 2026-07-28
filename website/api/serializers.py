"""
DRF serializers for the public read-only API (#1268).

These deliberately expose only fields that are already public on the website and
build **absolute** URLs for media (PDFs, thumbnails) and human-facing pages, so a
consumer gets click-through links rather than bare relative paths. Personal
contact details (e.g. ``Person.email``) are intentionally *not* serialized to
avoid turning the API into an email-harvesting surface, even where they appear on
a member page.

Image fields follow one rule: ``thumbnail`` is a *cropped, sized derivative*
(honoring the editor's crop box, same as the site renders) and ``image_original``
is the raw upload. See :func:`cropped_thumbnail_url` and #1432.

Existing model helpers are reused rather than re-deriving formatting:
``Person.get_full_name`` / ``get_current_title``, ``Publication`` citation
helpers, ``Project.get_display_short_name``, ``Grant.start_date`` / ``grant_url``.
"""

from django.urls import NoReverseMatch, reverse
from rest_framework import serializers

from website.models import Grant, Person, Project, ProjectRole, Publication
from website.utils.thumbnail_utils import get_cropped_thumbnail

# Sizes for the cropped derivatives the API serves as ``thumbnail`` (#1432).
#
# Each keeps the aspect ratio of the corresponding model's ImageRatioField --
# Person's crop box is square (245x245), Project's is 15:9 (500x300). A mismatch
# would make easy-thumbnails center-crop a second time on top of the editor's
# box, which is what clipped heads off the news cards in #1424.
#
# Both are ~2x what the site itself renders, so a consumer can draw a 128px
# avatar (or a 500px-wide project card) sharply on a HiDPI display.
API_PERSON_THUMBNAIL_SIZE = (256, 256)
API_PROJECT_THUMBNAIL_SIZE = (1000, 600)


def abs_media_url(request, filefield):
    """Return an absolute URL for a File/ImageField, or ``None`` if unset.

    ``filefield.url`` raises ``ValueError`` when the field has no file, so we
    guard that and fall back to a relative URL when there's no request in
    context (e.g. serializing outside a request cycle).
    """
    if not filefield:
        return None
    try:
        url = filefield.url
    except ValueError:
        return None
    return request.build_absolute_uri(url) if request is not None else url


def cropped_thumbnail_url(request, image_field, size, box=None):
    """Absolute URL of the cropped derivative of ``image_field`` at ``size``.

    Falls back to the original image when generation fails (a bad/missing source
    file), so ``thumbnail`` is never null for a row that *has* an image; returns
    ``None`` when there's no image at all. Reuses the same easy-thumbnails
    options the site's templates pass, so the API shares their cached files.
    """
    thumbnail = get_cropped_thumbnail(image_field, size, box)
    return abs_media_url(request, thumbnail or image_field)


def abs_page_url(request, url_name, *args):
    """Absolute URL for a named route, tolerant of reverse failures.

    Returns ``None`` rather than raising if the route can't be reversed (e.g. a
    slug containing characters the URL pattern doesn't accept), so one odd row
    never 500s a whole list response.
    """
    try:
        path = reverse(url_name, args=args)
    except NoReverseMatch:
        return None
    return request.build_absolute_uri(path) if request is not None else path


class PersonSummarySerializer(serializers.ModelSerializer):
    """Compact person representation, used when nested in publications/roles.

    ``thumbnail`` is the cropped 256x256 headshot -- the same derivative the
    site's own pages render, honoring the crop box an editor set in the admin.
    ``image_original`` is the raw upload, which can be tens of megabytes; only
    reach for it if you genuinely need full resolution (#1432).
    """

    name = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()
    image_original = serializers.SerializerMethodField()

    class Meta:
        model = Person
        fields = ["id", "url_name", "name", "url", "thumbnail", "image_original"]

    def get_name(self, obj):
        return obj.get_full_name()

    def get_url(self, obj):
        return abs_page_url(
            self.context.get("request"), "website:member_by_name", obj.url_name
        )

    def get_thumbnail(self, obj):
        return cropped_thumbnail_url(
            self.context.get("request"),
            obj.image,
            API_PERSON_THUMBNAIL_SIZE,
            obj.cropping,
        )

    def get_image_original(self, obj):
        return abs_media_url(self.context.get("request"), obj.image)


class PersonSerializer(PersonSummarySerializer):
    """Full person representation for the people detail/list endpoints.

    Extends the summary with bio, current affiliation, and the public social/web
    links. ``email`` is intentionally omitted (see module docstring).

    ``current_title`` / ``current_school`` / ``current_department`` all come from
    the person's *latest* Position, so for an alum they describe their last lab
    position, not their present-day employer. For what someone was during a
    specific project stint, use ``ProjectRoleSerializer``'s ``position_*`` fields.
    """

    current_title = serializers.SerializerMethodField()
    current_school = serializers.SerializerMethodField()
    current_department = serializers.SerializerMethodField()

    class Meta(PersonSummarySerializer.Meta):
        fields = PersonSummarySerializer.Meta.fields + [
            "first_name",
            "middle_name",
            "last_name",
            "current_title",
            "current_school",
            "current_department",
            "bio",
            "personal_website",
            "github",
            "twitter",
            "bluesky",
            "threads",
            "mastodon",
            "linkedin",
            "orcid",
            "google_scholar",
        ]

    def get_current_title(self, obj):
        # Person.get_current_title is a cached_property, not a method.
        return obj.get_current_title

    def get_current_school(self, obj):
        # Person.get_current_school is a cached_property, not a method.
        return obj.get_current_school

    def get_current_department(self, obj):
        # Person.get_current_department is a cached_property, not a method.
        return obj.get_current_department


class ProjectSummarySerializer(serializers.ModelSerializer):
    """Compact project representation, used when nested in publications/grants."""

    name = serializers.CharField(read_only=True)
    display_short_name = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ["id", "short_name", "name", "display_short_name", "url"]

    def get_display_short_name(self, obj):
        return obj.get_display_short_name()

    def get_url(self, obj):
        return abs_page_url(
            self.context.get("request"), "website:project", obj.short_name
        )


class ProjectSerializer(ProjectSummarySerializer):
    """Full project representation for the projects detail/list endpoints.

    As with people, ``thumbnail`` is the cropped 1000x600 derivative of the
    gallery image (honoring ``Project.cropping``) and ``image_original`` is the
    raw upload (#1432).
    """

    thumbnail = serializers.SerializerMethodField()
    image_original = serializers.SerializerMethodField()
    keywords = serializers.SerializerMethodField()
    project_umbrellas = serializers.SerializerMethodField()

    class Meta(ProjectSummarySerializer.Meta):
        fields = ProjectSummarySerializer.Meta.fields + [
            "summary",
            "about",
            "start_date",
            "end_date",
            "website",
            "data_url",
            "featured_code_repo_url",
            "thumbnail",
            "image_original",
            "keywords",
            "project_umbrellas",
        ]

    def get_thumbnail(self, obj):
        return cropped_thumbnail_url(
            self.context.get("request"),
            obj.gallery_image,
            API_PROJECT_THUMBNAIL_SIZE,
            obj.cropping,
        )

    def get_image_original(self, obj):
        return abs_media_url(self.context.get("request"), obj.gallery_image)

    def get_keywords(self, obj):
        return [kw.keyword for kw in obj.keywords.all()]

    def get_project_umbrellas(self, obj):
        return [umb.name for umb in obj.project_umbrellas.all()]


class SponsorSummarySerializer(serializers.Serializer):
    """Minimal sponsor info nested inside a grant."""

    name = serializers.CharField()
    short_name = serializers.CharField()


class GrantSerializer(serializers.ModelSerializer):
    """A funding grant. ``start_date`` and ``grant_url`` are model properties
    aliasing the shared Artifact ``date`` / ``forum_url`` fields."""

    sponsor = SponsorSummarySerializer(read_only=True)
    grant_url = serializers.URLField(read_only=True)
    start_date = serializers.DateField(read_only=True)
    projects = ProjectSummarySerializer(many=True, read_only=True)

    class Meta:
        model = Grant
        fields = [
            "id",
            "title",
            "sponsor",
            "grant_id",
            "grant_url",
            "start_date",
            "end_date",
            "projects",
        ]


class PublicationListSerializer(serializers.ModelSerializer):
    """List representation of a publication.

    ``authors`` preserves the editor-defined order (SortedManyToManyField).
    ``forum_name`` is the formatted "Proceedings of …" string, not the raw
    field. Media links are absolute.
    """

    authors = PersonSummarySerializer(many=True, read_only=True)
    projects = ProjectSummarySerializer(many=True, read_only=True)
    year = serializers.SerializerMethodField()
    venue_type = serializers.CharField(source="pub_venue_type", read_only=True)
    forum_name = serializers.SerializerMethodField()
    pdf_url = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = Publication
        fields = [
            "id",
            "title",
            "authors",
            "date",
            "year",
            "venue_type",
            "forum_name",
            "forum_url",
            "doi",
            "official_url",
            "arxiv_url",
            "code_repo_url",
            "award",
            "pdf_url",
            "thumbnail",
            "projects",
        ]

    def get_year(self, obj):
        return obj.date.year if obj.date else None

    def get_forum_name(self, obj):
        return obj.get_formatted_forum_name()

    def get_pdf_url(self, obj):
        return abs_media_url(self.context.get("request"), obj.pdf_file)

    def get_thumbnail(self, obj):
        return abs_media_url(self.context.get("request"), obj.thumbnail)


class PublicationDetailSerializer(PublicationListSerializer):
    """Detail representation: adds a formatted citation and BibTeX."""

    citation_html = serializers.SerializerMethodField()
    bibtex = serializers.SerializerMethodField()

    class Meta(PublicationListSerializer.Meta):
        fields = PublicationListSerializer.Meta.fields + [
            "book_title",
            "publisher",
            "isbn",
            "num_pages",
            "peer_reviewed",
            "citation_html",
            "bibtex",
        ]

    def get_citation_html(self, obj):
        return obj.get_citation_as_html()

    def get_bibtex(self, obj):
        # Plain newlines + no HTML hyperlinks: consumers want raw BibTeX, not
        # the HTML-decorated variant used on the site.
        return obj.get_citation_as_bibtex(newline="\n", use_hyperlinks=False)


class ProjectRoleSerializer(serializers.ModelSerializer):
    """A person's role on a project (start/end, lead type, active flag).

    The ``position_*`` fields describe the person *over the span of this role* --
    title and school from the latest Position overlapping it (#1426, #1435). An
    ongoing role reports what they are today ("Professor, UW"); a stint that
    ended in 2016 still reads "Undergrad, UMD" even if that person is a professor
    now. They're ``null`` for someone with no Position on record. Named
    ``position_*`` (not bare ``title``) so they don't read as part of ``role``,
    which is the editor-written free-text description of the work.
    """

    person = PersonSummarySerializer(read_only=True)
    is_active = serializers.SerializerMethodField()
    position_title = serializers.SerializerMethodField()
    position_school = serializers.SerializerMethodField()
    position_school_abbreviated = serializers.SerializerMethodField()

    class Meta:
        model = ProjectRole
        fields = [
            "person",
            "role",
            "lead_project_role",
            "position_title",
            "position_school",
            "position_school_abbreviated",
            "start_date",
            "end_date",
            "is_active",
        ]

    def get_is_active(self, obj):
        return obj.is_active()

    # ProjectRole.position_during_role is a cached_property, so the three fields
    # below resolve it once per row (and ride the view's prefetch -- see the
    # model helper).
    def get_position_title(self, obj):
        position = obj.position_during_role
        return position.title if position else None

    def get_position_school(self, obj):
        position = obj.position_during_role
        return position.school if position else None

    def get_position_school_abbreviated(self, obj):
        position = obj.position_during_role
        return position.get_school_abbreviated() if position else None
