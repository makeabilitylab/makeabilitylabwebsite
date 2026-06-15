"""
View for the internal "project people" page.

This page lets lab members browse the people associated with projects and tweak
the display (filter / sort / group / show-or-hide fields) from a collapsible
sidebar. Its main use is generating acknowledgment grids of headshots for talks
and papers. All filtering, sorting, and grouping happens client-side for instant
updates, so the view's job is simply to emit a complete JSON snapshot of the data.

Three JSON blobs are placed in the template context:
    - projects_json: every project, for the sidebar (id, name, short_name,
      is_active, people_count).
    - people_json: every Person, with position, school/department, lab dates,
      per-project role durations, and publication indicators.
    - abstracted_titles_json: the ordered abstracted-title groups used for the
      "group by position" mode.

The client persists its display options in the URL query string; the server does
not read those parameters — it always returns the full dataset.
"""

import json
import logging

from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count, Q
from django.shortcuts import render

# easy-thumbnails generates the per-person headshot thumbnails server-side.
from easy_thumbnails.files import get_thumbnailer

from website.models import Person, Project, Publication
from website.models.position import Position, Title
from website.models.publication import PubType
from datetime import date

_logger = logging.getLogger(__name__)

# Matches PERSON_THUMBNAIL_SIZE in website/models/person.py.
PERSON_THUMBNAIL_SIZE = (245, 245)


def _build_projects_payload():
    """
    Builds the sidebar project list.

    Returns a list of dicts (one per project, ordered by name). people_count is
    annotated in the query so this does not issue a query per project.
    """
    projects = (
        Project.objects.annotate(num_people=Count("projectrole__person", distinct=True))
        .order_by("name")
    )
    return [
        {
            "id": project.id,
            "name": project.name,
            "short_name": project.short_name,
            "is_active": not project.has_ended(),
            "people_count": project.num_people,
        }
        for project in projects
    ]


def _build_phd_advisee_ids(director):
    """
    Returns the set of Person ids who are PhD advisees of `director`.

    This mirrors :meth:`website.models.person.Person.is_phd_advisee_of` (a person
    advised or co-advised by the director as a PhD student, counted only while the
    position is active or once they have a dissertation) but computes it in a few
    bulk queries instead of one query per person.
    """
    if director is None:
        return set()

    phd_positions = Position.objects.filter(title=Title.PHD_STUDENT).filter(
        Q(advisor=director) | Q(co_advisor=director)
    )
    advised_ids = set(phd_positions.values_list("person_id", flat=True))
    active_advised_ids = set(
        phd_positions.filter(
            Q(end_date__isnull=True) | Q(end_date__gte=date.today())
        ).values_list("person_id", flat=True)
    )
    dissertation_author_ids = set(
        Publication.objects.filter(
            pub_venue_type=PubType.PHD_DISSERTATION
        ).values_list("authors__id", flat=True)
    )

    # Active advisees always count; past advisees only once they have a dissertation.
    return {
        person_id
        for person_id in advised_ids
        if person_id in active_advised_ids or person_id in dissertation_author_ids
    }


def _build_thumbnail_url(person):
    """
    Returns the URL of `person`'s cropped headshot thumbnail.

    Uses easy-thumbnails together with django-image-cropping (the crop box, if set,
    lives on person.cropping). Falls back to the original image URL if thumbnail
    generation fails, or to '' if the person has no image.
    """
    if not person.image:
        return ""

    options = {
        "size": PERSON_THUMBNAIL_SIZE,
        "crop": True,
        "upscale": True,
        "detail": True,
    }
    if person.cropping:
        options["box"] = person.cropping

    try:
        thumbnail = get_thumbnailer(person.image).get_thumbnail(options)
        return thumbnail.url if thumbnail else ""
    except Exception:
        _logger.warning(
            "Thumbnail generation failed for %s; falling back to original image.",
            person,
            exc_info=True,
        )
        return person.image.url


def _build_project_roles(person, today):
    """
    Aggregates `person`'s ProjectRoles into per-project totals.

    Returns a dict keyed by project short_name with total_days worked and the
    overall (earliest start, latest end) span. A person can have several roles on
    the same project, so durations are summed and the span is widened across them.
    Dates are left as date objects; DjangoJSONEncoder serializes them to ISO
    'YYYY-MM-DD' strings, which the client parses.
    """
    project_roles = {}
    for role in person.projectrole_set.all():
        short_name = role.project.short_name
        start = role.start_date
        end = role.end_date or today

        entry = project_roles.get(short_name)
        if entry is None:
            project_roles[short_name] = {
                "total_days": (end - start).days,
                "start_date": start,
                "end_date": end,
            }
        else:
            entry["total_days"] += (end - start).days
            entry["start_date"] = min(entry["start_date"], start)
            entry["end_date"] = max(entry["end_date"], end)
    return project_roles


def _build_person_payload(person, director_id, is_phd_advisee, today):
    """Builds the JSON-serializable dict for a single Person."""
    # The prefetched positions let us pick earliest/latest in Python (sorted by
    # start_date) without the per-person queries the model's cached properties make.
    positions = sorted(person.position_set.all(), key=lambda p: p.start_date)
    earliest_position = positions[0] if positions else None
    latest_position = positions[-1] if positions else None

    if latest_position:
        abstracted_title = Position.get_abstracted_title(latest_position)
        title_index = latest_position.get_title_index()
    else:
        abstracted_title = "Unknown"
        title_index = Position.TITLE_ORDER_MAPPING[Title.UNKNOWN]

    # Projects this person has published on (drives the "published" highlight).
    projects_published_on = sorted(
        {
            project.short_name
            for pub in person.publication_set.all()
            for project in pub.projects.all()
        }
    )

    return {
        "id": person.id,
        "first_name": person.first_name,
        "last_name": person.last_name,
        "full_name": person.get_full_name(),
        "url_name": person.url_name,
        "is_director": person.id == director_id,
        "is_phd_advisee": is_phd_advisee,
        # Pre-computed thumbnail URL.
        "image_url": _build_thumbnail_url(person),
        # Position info.
        "title": latest_position.title if latest_position else "Unknown",
        "abstracted_title": abstracted_title or "Unknown",
        # School / department info.
        "school": latest_position.school if latest_position else "",
        "school_abbreviated": (
            latest_position.get_school_abbreviated() if latest_position else ""
        ),
        "department": latest_position.department if latest_position else "",
        "department_abbreviated": (
            latest_position.get_department_abbreviated() if latest_position else ""
        ),
        # Lab dates.
        "lab_start_date": earliest_position.start_date if earliest_position else None,
        "lab_end_date": latest_position.end_date if latest_position else None,
        "date_range_str": (
            latest_position.get_date_range_as_str() if latest_position else ""
        ),
        # Seniority: lower index = more senior (see Position.TITLE_ORDER_MAPPING).
        "seniority_index": title_index,
        # Per-project role durations.
        "project_roles": _build_project_roles(person, today),
        "projects_published_on": projects_published_on,
        "has_any_publication": bool(person.publication_set.all()),
        # Role (Member vs Collaborator), used by the client-side filters.
        "role": latest_position.role if latest_position else "Unknown",
    }


def view_project_people(request):
    """
    Renders the project-people page with the full people/projects dataset.

    Args:
        request: Django HTTP request object.

    Returns:
        Rendered ``website/view_project_people.html`` with three JSON context
        blobs (projects, people, abstracted titles) for client-side rendering.
    """
    today = date.today()

    # The lab director is identified by their Title.DIRECTOR position. Both the
    # is_director flag and the PhD-advisee check derive from this single Person so
    # they cannot disagree.
    director = (
        Person.objects.filter(position__title=Title.DIRECTOR).distinct().first()
    )
    director_id = director.id if director else None
    phd_advisee_ids = _build_phd_advisee_ids(director)

    # Every Person (the page includes a "show all people" mode). Prefetch the
    # relations the payload reads so building it stays query-free per person.
    all_people = Person.objects.prefetch_related(
        "position_set",
        "projectrole_set__project",
        "publication_set__projects",
    )
    people_data = [
        _build_person_payload(person, director_id, person.id in phd_advisee_ids, today)
        for person in all_people
    ]

    # Abstracted-title groups (mix of plain strings and Title enum members).
    abstracted_titles = [
        t.value if hasattr(t, "value") else str(t)
        for t in Position.get_sorted_abstracted_titles()
    ]

    context = {
        "projects_json": json.dumps(_build_projects_payload(), cls=DjangoJSONEncoder),
        "people_json": json.dumps(people_data, cls=DjangoJSONEncoder),
        "abstracted_titles_json": json.dumps(abstracted_titles, cls=DjangoJSONEncoder),
    }
    return render(request, "website/view_project_people.html", context)
