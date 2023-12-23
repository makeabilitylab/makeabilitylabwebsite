from django.conf import settings # for access to settings variables, see https://docs.djangoproject.com/en/4.0/topics/settings/#using-settings-in-python-code
from website.models import Banner, Person, News
import website.utils.ml_utils as ml_utils 
from django.shortcuts import render, get_object_or_404

# For logging
import time
import logging

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

def member(request, member_id):
    func_start_time = time.perf_counter()
    _logger.debug(f"Starting views/member member_id={member_id} at {func_start_time:0.4f}")

    news_items_num = 5  # Defines the number of news items that will be selected
    # all_banners = Banner.objects.filter(page=Banner.PEOPLE)
    # displayed_banners = ml_utils.choose_banners(all_banners)

    # This code block gets a person object either from the member id or the url_name.
    # If the member_id is a digit, it's assumed to be the primary key (pk) of the Person object
    # The get_object_or_404 function is then used to retrieve the Person object with this pk. 
    # If no such Person object exists, the function will raise a 404 error.
    # If the member_id is not a digit, it's assumed to be the url-friendly name (url_name).
    if (member_id.isdigit()):
        person = get_object_or_404(Person, pk=member_id)
    else:
        person = get_object_or_404(Person, url_name__iexact=member_id)

    # Returns QuerySet of News objects that mention the specified person. 
    # The order_by('-date') part sorts the QuerySet by date in descending order 
    # (so the most recent news comes first), and [:4] limits the QuerySet to 
    # the first 4 objects.
    news = News.objects.filter(people=person).order_by('-date')[:4]
    latest_position = person.get_latest_position
    publications = person.publication_set.order_by('-date')
    talks = person.talk_set.order_by('-date')
    project_roles = person.projectrole_set.order_by('start_date')
    projects = person.get_projects

    # filter projects to those that have a thumbnail and have been published
    # TODO: might consider moving this to ml_utils so we have consistent determination
    # of what projects to show publicly
    filtered_projects = list()
    for proj in projects:
        if proj.gallery_image is not None and proj.has_publication():
            filtered_projects.append(proj)
    projects = filtered_projects

    context = {'person': person,
               'news': news,
               'talks': talks,
               'publications': publications,
               'project_roles': project_roles,
               'projects' : projects,
               'position' : latest_position,
               # 'banners': displayed_banners,
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