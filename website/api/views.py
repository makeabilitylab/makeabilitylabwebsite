"""
Read-only DRF viewsets for the public API (#1268).

All viewsets are ``ReadOnlyModelViewSet`` (list + retrieve only). Filtering is
done with explicit query params in ``get_queryset`` rather than a filter library
to avoid a new dependency. Querysets ``prefetch_related`` / ``select_related``
the relations the serializers touch, per the repo's N+1 notes.

Visibility: projects are gated to ``is_visible=True`` (so unpublished projects
404), and the people list is scoped to actual lab members (people with at least
one Position), not every co-author in the database.
"""

from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from website.models import Grant, Person, Project, ProjectRole, Publication
from website.models.project_role import LeadProjectRoleTypes

from .serializers import (
    GrantSerializer,
    ProjectRoleSerializer,
    ProjectSerializer,
    PersonSerializer,
    PublicationDetailSerializer,
    PublicationListSerializer,
)

# Ordering values we accept on ?ordering= for publications. Whitelisted so a
# consumer can't order by (and thereby probe) arbitrary columns.
_PUB_ORDERING = {"date", "-date", "title", "-title"}

# Maps each lead-role type to its response key in the leadership endpoint.
# Ordered so the response keys are stable/predictable.
_LEAD_BUCKETS = {
    LeadProjectRoleTypes.PI: "pis",
    LeadProjectRoleTypes.CO_PI: "co_pis",
    LeadProjectRoleTypes.STUDENT_LEAD: "student_leads",
    LeadProjectRoleTypes.POSTDOC_LEAD: "postdoc_leads",
    LeadProjectRoleTypes.RESEARCH_SCIENTIST_LEAD: "research_scientist_leads",
}


class ApiPagination(PageNumberPagination):
    """Page-number pagination with a caller-tunable, capped page size.

    ``?page_size=5`` is what powers a "top 5 recent" list; ``max_page_size``
    stops a caller from requesting an unbounded page. Default page size comes
    from ``settings.REST_FRAMEWORK['PAGE_SIZE']``.
    """

    page_size_query_param = "page_size"
    max_page_size = 100


class _PaginatedActionMixin:
    """Helper so ``@action`` sub-resources paginate like top-level lists."""

    def _paginated(self, queryset, serializer_cls):
        page = self.paginate_queryset(queryset)
        context = self.get_serializer_context()
        if page is not None:
            data = serializer_cls(page, many=True, context=context).data
            return self.get_paginated_response(data)
        data = serializer_cls(queryset, many=True, context=context).data
        return Response(data)


class PublicationViewSet(ReadOnlyModelViewSet):
    """Publications, newest first.

    Filters (all optional, combinable):
      * ``?project=<short_name>`` -- pubs attached to a project.
      * ``?author=<url_name>``    -- pubs by a person.
      * ``?year=<yyyy>``          -- pubs in a calendar year.
      * ``?type=<venue>``         -- by ``pub_venue_type`` (e.g. Conference).
      * ``?ordering=`` one of ``date``/``-date``/``title``/``-title`` (default ``-date``).

    Powers both driving use cases: ``?author=jonfroehlich&page_size=5`` (recent
    pubs widget) and ``?project=projectsidewalk`` (a project's publications).
    """

    pagination_class = ApiPagination

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PublicationDetailSerializer
        return PublicationListSerializer

    def get_queryset(self):
        qs = Publication.objects.prefetch_related("authors", "projects")
        params = self.request.query_params

        project = params.get("project")
        if project:
            qs = qs.filter(projects__short_name__iexact=project)

        author = params.get("author")
        if author:
            qs = qs.filter(authors__url_name__iexact=author)

        year = params.get("year")
        if year and year.isdigit():
            qs = qs.filter(date__year=int(year))

        venue = params.get("type")
        if venue:
            qs = qs.filter(pub_venue_type__iexact=venue)

        ordering = params.get("ordering")
        ordering = ordering if ordering in _PUB_ORDERING else "-date"
        return qs.order_by(ordering).distinct()


class PersonViewSet(ReadOnlyModelViewSet):
    """Lab members (people with at least one Position), looked up by ``url_name``."""

    serializer_class = PersonSerializer
    pagination_class = ApiPagination
    lookup_field = "url_name"

    def get_queryset(self):
        return (
            Person.objects.filter(position__isnull=False)
            .distinct()
            .order_by("last_name", "first_name")
        )


class GrantViewSet(ReadOnlyModelViewSet):
    """Funding grants, newest first.

    Filters: ``?project=<short_name>``, ``?sponsor=<sponsor short_name>``.
    """

    serializer_class = GrantSerializer
    pagination_class = ApiPagination

    def get_queryset(self):
        qs = Grant.objects.select_related("sponsor").prefetch_related("projects")
        project = self.request.query_params.get("project")
        if project:
            qs = qs.filter(projects__short_name__iexact=project)
        sponsor = self.request.query_params.get("sponsor")
        if sponsor:
            qs = qs.filter(sponsor__short_name__iexact=sponsor)
        return qs.order_by("-date").distinct()


class ProjectViewSet(_PaginatedActionMixin, ReadOnlyModelViewSet):
    """Publicly visible projects, looked up by ``short_name``.

    Sub-resources (Project Sidewalk's needs):
      * ``/{short_name}/publications/`` -- the project's publications.
      * ``/{short_name}/grants/``       -- grants funding the project.
      * ``/{short_name}/people/``       -- everyone with a role, plus their role.
      * ``/{short_name}/leadership/``   -- all-time PIs / Co-PIs / leads (current + past).
    """

    serializer_class = ProjectSerializer
    pagination_class = ApiPagination
    lookup_field = "short_name"

    def get_queryset(self):
        return (
            Project.objects.filter(is_visible=True)
            .prefetch_related("keywords", "project_umbrellas")
            .order_by("name")
        )

    @action(detail=True, methods=["get"])
    def publications(self, request, short_name=None):
        project = self.get_object()
        qs = (
            Publication.objects.filter(projects=project)
            .prefetch_related("authors", "projects")
            .order_by("-date")
            .distinct()
        )
        return self._paginated(qs, PublicationListSerializer)

    @action(detail=True, methods=["get"])
    def grants(self, request, short_name=None):
        project = self.get_object()
        qs = (
            project.grant_set.select_related("sponsor")
            .prefetch_related("projects")
            .order_by("-date")
        )
        return self._paginated(qs, GrantSerializer)

    @action(detail=True, methods=["get"])
    def people(self, request, short_name=None):
        # Returns ProjectRoles (a person can hold more than one role, each with
        # its own date range), not distinct people.
        project = self.get_object()
        qs = (
            ProjectRole.objects.filter(project=project)
            .select_related("person")
            .order_by("person__last_name", "person__first_name", "start_date")
        )
        return self._paginated(qs, ProjectRoleSerializer)

    @action(detail=True, methods=["get"])
    def leadership(self, request, short_name=None):
        # Returns *all* leadership roles for all time -- current and past --
        # grouped by lead type. We query ProjectRole directly rather than reuse
        # Project.get_project_leadership(): that helper is built for the public
        # page's current-vs-past display and computes "inactive" per *person*,
        # so it drops a person's past lead roles once they hold any active role.
        # Each returned role carries its own is_active flag, so a consumer can
        # still separate current from past leadership client-side.
        project = self.get_object()
        roles = (
            ProjectRole.objects.filter(
                project=project, lead_project_role__in=list(_LEAD_BUCKETS)
            )
            .select_related("person")
            .order_by("-start_date")
        )
        context = self.get_serializer_context()

        grouped = {key: [] for key in _LEAD_BUCKETS.values()}
        for role in roles:
            grouped[_LEAD_BUCKETS[role.lead_project_role]].append(role)

        return Response(
            {
                key: ProjectRoleSerializer(items, many=True, context=context).data
                for key, items in grouped.items()
            }
        )
