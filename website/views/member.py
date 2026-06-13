from django.conf import settings # for access to settings variables, see https://docs.djangoproject.com/en/4.0/topics/settings/#using-settings-in-python-code
from website.models import Person, News, Video
import website.utils.ml_utils as ml_utils
from website.utils.bio_utils import auto_generate_bio
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.core.exceptions import MultipleObjectsReturned

# For logging
import time
import logging
from django.http import Http404

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

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
            # This should not happen if url_name uniqueness is working correctly
            # Log error and return the most recently modified person as fallback
            _logger.error(f"Multiple people found with url_name={member_name}! This indicates url_name uniqueness is broken. Returning most recent.")
            person = Person.objects.filter(url_name__iexact=member_name).order_by('-modified_date').first()
            if person is None:
                raise Http404("No person matches the given query.")
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
    publications = (person.publication_set
                    .prefetch_related('authors', 'projects', 'keywords')
                    .order_by('-date'))
    talks = (person.talk_set
             .select_related('video')
             .prefetch_related('authors', 'publication_set', 'projects')
             .order_by('-date'))
    videos = get_videos_by_author(person)
    project_roles = person.projectrole_set.order_by('-start_date')
    projects = person.get_projects

    # Sort projects: active first (not ended), then by most recent start_date
    projects = sorted(
        projects,
        key=lambda proj: (
            # First sort key: active projects first
            # has_ended() returns False for active, True for ended
            # Since False < True, active projects come first
            proj.has_ended(),
            # Second sort key: most recent start_date first (descending)
            -(proj.start_date.toordinal() if proj.start_date else 0)
        )
    )

    left_align_headers = (len(projects) <= 4 and len(publications) <= 3 and 
                          len(talks) <= 3 and len(videos) <= 3)
    
    auto_generated_bio = ""
    if not person.bio:
        auto_generated_bio = auto_generate_bio(person)

    # filter projects to those that have a thumbnail and have been published
    # TODO: might consider moving this to ml_utils so we have consistent determination
    # of what projects to show publicly
    filtered_projects = list()
    for proj in projects:
        if proj.gallery_image is not None and proj.has_publication():
            filtered_projects.append(proj)
    projects = filtered_projects

    context = {'person': person,
               'auto_generated_bio': auto_generated_bio,
               'news': news,
               'talks': talks,
               'videos': videos,
               'publications': publications,
               'project_roles': project_roles,
               'projects' : projects,
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

def get_videos_by_author(person):
    """Returns a queryset of videos that the given person is an author on"""
    return (Video.objects
            .select_related('publication')
            .prefetch_related('projects')
            .filter(Q(publication__authors=person) | Q(talk__authors=person))
            .distinct()
            .order_by('-date'))

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