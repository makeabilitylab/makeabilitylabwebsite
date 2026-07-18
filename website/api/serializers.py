"""
DRF serializers for the public read-only API (#1268).

These deliberately expose only fields that are already public on the website and
build **absolute** URLs for media (PDFs, thumbnails) and human-facing pages, so a
consumer gets click-through links rather than bare relative paths. Personal
contact details (e.g. ``Person.email``) are intentionally *not* serialized to
avoid turning the API into an email-harvesting surface, even where they appear on
a member page.

Existing model helpers are reused rather than re-deriving formatting:
``Person.get_full_name`` / ``get_current_title``, ``Publication`` citation
helpers, ``Project.get_display_short_name``, ``Grant.start_date`` / ``grant_url``.
"""

from django.urls import NoReverseMatch, reverse
from rest_framework import serializers

from website.models import Grant, Person, Project, ProjectRole, Publication


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
    """Compact person representation, used when nested in publications/roles."""

    name = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = Person
        fields = ["id", "url_name", "name", "url", "thumbnail"]

    def get_name(self, obj):
        return obj.get_full_name()

    def get_url(self, obj):
        return abs_page_url(
            self.context.get("request"), "website:member_by_name", obj.url_name
        )

    def get_thumbnail(self, obj):
        return abs_media_url(self.context.get("request"), obj.image)


class PersonSerializer(PersonSummarySerializer):
    """Full person representation for the people detail/list endpoints.

    Extends the summary with bio, current title, and the public social/web
    links. ``email`` is intentionally omitted (see module docstring).
    """

    current_title = serializers.SerializerMethodField()

    class Meta(PersonSummarySerializer.Meta):
        fields = PersonSummarySerializer.Meta.fields + [
            "first_name",
            "middle_name",
            "last_name",
            "current_title",
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
    """Full project representation for the projects detail/list endpoints."""

    thumbnail = serializers.SerializerMethodField()
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
            "keywords",
            "project_umbrellas",
        ]

    def get_thumbnail(self, obj):
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
            "funding_amount",
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
    """A person's role on a project (start/end, lead type, active flag)."""

    person = PersonSummarySerializer(read_only=True)
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = ProjectRole
        fields = [
            "person",
            "role",
            "lead_project_role",
            "start_date",
            "end_date",
            "is_active",
        ]

    def get_is_active(self, obj):
        return obj.is_active()
