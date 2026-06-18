from django.conf import settings # for access to settings variables, see https://docs.djangoproject.com/en/4.0/topics/settings/#using-settings-in-python-code
from website.models import Person, News, Video
import website.utils.ml_utils as ml_utils
from website.utils.bio_utils import auto_generate_bio
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.core.exceptions import MultipleObjectsReturned
from django.http import Http404, JsonResponse
from django.template.loader import render_to_string

from datetime import date

# For logging
import time
import logging

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

# How many of each artifact type the member page renders server-side on first
# paint (the *desktop* count) and, equivalently, the batch size fetched by each
# subsequent AJAX "See more" click (#1110).
#
# Mobile shows fewer than this (see ARTIFACT_MOBILE_PAGE_SIZES). Importantly,
# the full desktop count is ALWAYS in the initial HTML regardless of viewport;
# a CSS rule (member.css) merely hides the overflow on narrow screens. That's
# why the first "See more" tap on a phone is an instant CSS reveal with no
# network request, and only loads beyond the desktop count go to the server.
ARTIFACT_PAGE_SIZES = {
    'projects': 8,
    'publications': 6,
    'videos': 6,
    'talks': 8,
}

# How many of each artifact type are visible on small screens (<=576px, the
# point where every grid collapses to a single column). Enforced purely in CSS
# (member.css) via an :nth-child cap; passed to the template only so the
# load-more JS can decide whether a section needs a "See more" control and can
# announce the right counts. See the no-JS tradeoff note in member.css.
ARTIFACT_MOBILE_PAGE_SIZES = {
    'projects': 4,
    'publications': 3,
    'videos': 3,
    'talks': 4,
}

def member(request, member_name=None, member_id=None):
    func_start_time = time.perf_counter()
    _logger.debug(f"Starting views/member member_id={member_id} and member_name={member_name} at {func_start_time:0.4f}")

    # This code block gets a person object either from the member id or the url_name.
    # If the member_id is a digit, it's assumed to be the primary key (pk) of the Person object
    # The get_object_or_404 function is then used to retrieve the Person object with this pk. 
    # If no such Person object exists, the function will raise a 404 error.
    # If the member_id is not a digit, it's assumed to be the url-friendly name (url_name).
    person = None
    if member_id is not None:
        _logger.debug(f"Found a member_id={member_id}, checking for a person with that id")
        person = get_object_or_404(Person, id=member_id)
    elif member_name is not None:
        _logger.debug(f"Found a member_name={member_name}, checking for a url_name match")
        try:
            # Try a case-insensitive exact match
            person = get_object_or_404(Person, url_name__iexact=member_name)
        except MultipleObjectsReturned:
            # url_name is kept unique by Person.save() and the recompute_url_names
            # command (#1206/#1275), so this branch should be unreachable. If a
            # collision ever recurs, fail loudly with a clean 404 rather than a 500
            # or a silent .first() pick (which would make one namesake permanently
            # unreachable and could surface the wrong person). The fix is always to
            # re-run `manage.py recompute_url_names`, not to guess a winner here.
            _logger.error(
                f"Multiple people share url_name={member_name!r} — url_name uniqueness is "
                f"broken; run `manage.py recompute_url_names`. Returning 404.")
            raise Http404("No unique person matches the given query.")
        except Http404:
            _logger.debug(f"{member_name} not found for url_name, looking for closest match in database")
            closest_urlname = get_closest_urlname_in_database(member_name)
            person = get_object_or_404(Person, url_name__iexact=closest_urlname)

            # Redirect to the correct URL for the closest match
            return redirect('website:member_by_name', member_name=person.url_name)
    else:
        raise Http404("No person matches the given query.")

    news_items_num = 5  # Defines the number of news items that will be selected
    # all_banners = Banner.objects.filter(page=Banner.PEOPLE)
    # displayed_banners = ml_utils.choose_banners(all_banners)

    

    # Returns QuerySet of News objects that mention the specified person. 
    # The order_by('-date') part sorts the QuerySet by date in descending order 
    # (so the most recent news comes first), and [:4] limits the QuerySet to 
    # the first 4 objects.
    news = News.objects.filter(people=person).order_by('-date')[:4]
    latest_position = person.get_latest_position

    # Full, ordered sequences for each artifact type. These same helpers back
    # the member_artifacts AJAX endpoint, so the initial render and every "See
    # more" batch share one ordering (and one definition of "this person's
    # artifacts"). We slice them below for the first paint and only count() the
    # totals — we never materialize the whole list of (sometimes 100+) papers.
    publications = get_member_publications(person)
    talks = get_member_talks(person)
    videos = get_videos_by_author(person)
    projects = get_member_projects(person)  # a list (sorted in Python), not a queryset
    project_roles = person.projectrole_set.order_by('-start_date')

    publications_total = publications.count()
    talks_total = talks.count()
    videos_total = videos.count()
    projects_total = len(projects)

    # Left-align section headers only when every section is short enough to fit
    # in its first (desktop) row — i.e. nothing is truncated. Thresholds track
    # the desktop page sizes above.
    left_align_headers = (projects_total <= ARTIFACT_PAGE_SIZES['projects'] and
                          publications_total <= ARTIFACT_PAGE_SIZES['publications'] and
                          talks_total <= ARTIFACT_PAGE_SIZES['talks'] and
                          videos_total <= ARTIFACT_PAGE_SIZES['videos'])

    auto_generated_bio = ""
    if not person.bio:
        auto_generated_bio = auto_generate_bio(person)

    context = {'person': person,
               'auto_generated_bio': auto_generated_bio,
               'news': news,
               # Slice to the desktop page size for first paint. list()/[:n]
               # forces evaluation of just that slice; the *_total values above
               # carry the real counts the template needs for the "See more"
               # buttons and the "Recent" headings.
               'talks': list(talks[:ARTIFACT_PAGE_SIZES['talks']]),
               'videos': list(videos[:ARTIFACT_PAGE_SIZES['videos']]),
               'publications': list(publications[:ARTIFACT_PAGE_SIZES['publications']]),
               'projects': projects[:ARTIFACT_PAGE_SIZES['projects']],
               'talks_total': talks_total,
               'videos_total': videos_total,
               'publications_total': publications_total,
               'projects_total': projects_total,
               'page_sizes': ARTIFACT_PAGE_SIZES,
               'mobile_page_sizes': ARTIFACT_MOBILE_PAGE_SIZES,
               'project_roles': project_roles,
               'position' : latest_position,
               # 'banners': displayed_banners,
               'left_align_headers': left_align_headers,
               'debug': settings.DEBUG,
               'navbar_white': True,
               'page_title': person.get_full_name()}
    
    # Render is a Django shortcut (aka helper function). It combines a given template—in this case
    # member.html—with a context dictionary and returns an HttpResponse object with that rendered text.
    # See: https://docs.djangoproject.com/en/4.0/topics/http/shortcuts/#render
    render_func_start_time = time.perf_counter()
    render_response = render(request, 'website/member.html', context)
    render_func_end_time = time.perf_counter()
    _logger.debug(f"Took {render_func_end_time - render_func_start_time:0.4f} seconds to create render_response")

    func_end_time = time.perf_counter()
    _logger.debug(f"Prepared person={person} in {func_end_time - func_start_time:0.4f} seconds")
    context['render_time'] = func_end_time - func_start_time

    return render_response

def get_member_publications(person):
    """Publications authored by ``person``, newest first.

    The ``-id`` secondary sort is a deterministic tiebreaker: many papers share
    a single ``date``, and the "See more" control pages with ``[offset:offset+n]``
    slices across separate requests. Without a stable total order, equal-date
    rows could shuffle between pages and be dropped or duplicated.
    """
    return (person.publication_set
            .prefetch_related('authors', 'projects', 'keywords')
            .order_by('-date', '-id'))


def get_member_talks(person):
    """Talks given by ``person``, newest first (``-id`` tiebreaker; see
    :func:`get_member_publications` for why)."""
    return (person.talk_set
            .select_related('video')
            .prefetch_related('authors', 'publication_set', 'projects')
            .order_by('-date', '-id'))


def get_videos_by_author(person):
    """Videos that ``person`` is an author on (via an associated publication or
    talk), newest first (``-id`` tiebreaker; see
    :func:`get_member_publications`)."""
    return (Video.objects
            .select_related('publication')
            .prefetch_related('projects')
            .filter(Q(publication__authors=person) | Q(talk__authors=person))
            .distinct()
            .order_by('-date', '-id'))


def get_member_projects(person):
    """Visible projects ``person`` has worked on, ordered by each project's most
    recent activity (newest publication/talk/video) first.

    Ordering rationale (#1110): a member page should foreground the projects
    with the most recent *activity*, not the project's own ``start_date`` — a
    person can join a long-running project recently, and the old code sorted by
    ``start_date`` (after dropping order entirely by routing through a ``set``),
    which surfaced stale projects. We sort purely by most-recent-artifact date,
    descending — no active/ended grouping — with projects that have no artifacts
    sorting last (``date.min``).

    The ``pk`` tiebreaker makes the order fully deterministic across requests
    (``person.get_projects`` is an unordered ``set``), which the offset-based
    "See more" pagination in :func:`member_artifacts` relies on.

    Returns a list (the artifact-date key is computed in Python, so this can't
    stay a queryset).
    """
    projects = [proj for proj in person.get_projects if proj.is_visible]
    projects.sort(
        key=lambda proj: (proj.get_most_recent_artifact_date() or date.min, proj.pk),
        reverse=True,
    )
    return projects


# Maps an artifact_type URL segment to (ordered-sequence builder, snippet
# template, snippet context key, extra snippet context). Shared by the member
# page (indirectly, via the helpers above) and the member_artifacts endpoint so
# both render the identical markup.
_ARTIFACT_CONFIG = {
    'projects': (get_member_projects, 'snippets/display_project_snippet.html', 'project', {}),
    # Publications render VERTICAL here. The "Load more" control (hence this
    # endpoint) only appears when a member has more papers than the page size,
    # and that "many papers" case uses the scannable vertical list rather than
    # the compact 3-up card grid (#1110) — so appended papers are always vertical
    # rows. Members with few papers (<= page size) never reach this endpoint.
    'publications': (get_member_publications, 'snippets/display_pub_snippet.html', 'pub',
                     {'orientation': 'vertical'}),
    'videos': (get_videos_by_author, 'snippets/display_video_snippet.html', 'video', {}),
    'talks': (get_member_talks, 'snippets/display_talk_snippet.html', 'talk', {}),
}


def member_artifacts(request, member_id, artifact_type):
    """AJAX endpoint returning the next batch of a member's artifacts as HTML,
    for the per-section "See more" controls on the member page (#1110).

    Why HTML rather than JSON data: we render the very same snippet templates
    the page uses on first paint, so appended cards are byte-for-byte identical
    and stay accessible — there is no parallel client-side renderer to keep in
    sync. ``render_to_string(..., request=request)`` supplies ``MEDIA_URL`` and
    ``static`` via the normal context processors, which the talk/video snippets
    need.

    Keyed by primary key (not ``url_name``) because the page already knows
    ``person.id``; this deliberately sidesteps the fuzzy-name-match/redirect
    logic in :func:`member`.

    Query params:
        offset (int): how many items of this type the client already shows.
        all (str): when "1", return every remaining item from ``offset`` in one
            response (backs the "Load all" control) instead of a single batch.

    Returns JSON ``{html, has_more, next_offset}``. The server fixes the batch
    size (``ARTIFACT_PAGE_SIZES``) — the client cannot request an arbitrary page
    size (only "one batch" or "all the rest").
    """
    person = get_object_or_404(Person, id=member_id)

    if artifact_type not in _ARTIFACT_CONFIG:
        raise Http404(f"Unknown artifact type: {artifact_type}")
    builder, template_name, ctx_key, extra_ctx = _ARTIFACT_CONFIG[artifact_type]

    try:
        offset = max(int(request.GET.get('offset', 0)), 0)
    except (TypeError, ValueError):
        offset = 0

    page_size = ARTIFACT_PAGE_SIZES[artifact_type]
    load_all = request.GET.get('all') == '1'

    items = builder(person)
    total = len(items) if isinstance(items, list) else items.count()
    batch = items[offset:] if load_all else items[offset:offset + page_size]

    html = ''.join(
        render_to_string(template_name, {ctx_key: obj, **extra_ctx}, request=request)
        for obj in batch
    )
    next_offset = offset + len(batch)
    return JsonResponse({
        'html': html,
        'has_more': next_offset < total,
        'next_offset': next_offset,
    })

def get_closest_urlname_in_database(query_urlname, cutoff=0.8):
    """
    Retrieves the closest matching url_name from the database based on the provided query url_name.
    Args:
        query_urlname (str): The url_name to search for in the database.
        cutoff (float, optional): The similarity threshold for matching url_names. Defaults to 0.8.
    Returns:
        str: The closest matching url_name from the database.
    """
    
    all_urlnames = Person.objects.values_list('url_name', flat=True)
    return ml_utils.get_closest_match(query_urlname, all_urlnames, cutoff)