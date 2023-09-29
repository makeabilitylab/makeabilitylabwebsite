from django.conf import settings # for access to settings variables, see https://docs.djangoproject.com/en/4.0/topics/settings/#using-settings-in-python-code
from website.models import Banner, Publication, Talk, Video, Project, Person, News
import website.utils.ml_utils as ml_utils 
from django.shortcuts import render # for render https://docs.djangoproject.com/en/4.0/topics/http/shortcuts/#render

# For logging
import time
import logging

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

def index(request):
    func_start_time = time.perf_counter()
    _logger.debug(f"Starting views/index at {func_start_time:0.4f}")

    news_items_num = 7  # Defines the number of news items that will be selected
    papers_num = 10  # Defines the number of papers which will be selected
    talks_num = 8  # Defines the number of talks which will be selected
    videos_num = 4  # Defines the number of videos which will be selected
    projects_num = 8  # Defines the number of projects which will be selected

    all_banners = Banner.objects.filter(page=Banner.FRONTPAGE)
    displayed_banners = ml_utils.choose_banners(all_banners)
    print("settings.DEBUG =", settings.DEBUG)

    # Select recent news, papers, and talks.
    news_items = News.objects.order_by('-date')[:news_items_num]
    publications = Publication.objects.order_by('-date')[:papers_num]
    talks = Talk.objects.order_by('-date')[:talks_num]
    videos = Video.objects.order_by('-date')[:videos_num]

    # Sort projects by recency of publication
    # projects = Project.objects.all()
    # sorted(projects, key=lambda project: student[2])
    projects = Project.objects.all()
    projects = ml_utils.sort_projects_by_most_recent_pub(projects, settings.DEBUG)

    # we used to only filter out incomplete projects if DEBUG = TRUE; if not settings.DEBUG:
    projects = ml_utils.filter_incomplete_projects(projects)
    projects = projects[:projects_num]

    context = {'banners': displayed_banners,
               'news': news_items,
               'publications': publications,
               'talks': talks,
               'videos': videos,
               'projects': projects,
               'debug': settings.DEBUG}
    
    # People rendering
    func_end_time = time.perf_counter()
    _logger.debug(f"Rendered index in {func_end_time - func_start_time:0.4f} seconds")
    context['render_time'] = func_end_time - func_start_time

    # Render is a Django shortcut (aka helper function). It combines a given template—in this case
    # index.html—with a context dictionary and returns an HttpResponse object with that rendered text.
    # See: https://docs.djangoproject.com/en/4.0/topics/http/shortcuts/#render
    return render(request, 'website/index.html', context)