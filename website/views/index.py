from django.conf import settings # for access to settings variables, see https://docs.djangoproject.com/en/4.0/topics/settings/#using-settings-in-python-code
from website.models import Banner, Publication, Talk, Video, Project, Person, News
import website.utils.ml_utils as ml_utils 
from django.shortcuts import render # for render https://docs.djangoproject.com/en/4.0/topics/http/shortcuts/#render
from django.db.models import OuterRef, Subquery

# For logging
import time
import logging

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

MAX_NUM_NEWS_ITEMS = 5
MAX_NUM_PUBS = 6
MAX_NUM_PROJECTS = 8
MAX_NUM_TALKS = 8
MAX_NUM_VIDEOS = 3

def index(request):
    func_start_time = time.perf_counter()
    _logger.debug(f"Starting views/index at {func_start_time:0.4f}")

    all_banners = Banner.objects.filter(page=Banner.FRONTPAGE)

    # TODO: update how we choose banners using Django ORM vs. python
    displayed_banners = ml_utils.choose_banners(all_banners)

    # Select recent news, papers, and talks. Note that using Python's array-slicing syntax is the appropriate
    # way of limiting results in Django. See: https://docs.djangoproject.com/en/4.2/topics/db/queries/#limiting-querysets
    # Recall that Django  querysets are lazy. That means a query will hit the database only when you specifically 
    # ask for the result. In this case, when we iterate through in index.html
    news_items = News.objects.order_by('-date')[:MAX_NUM_NEWS_ITEMS]
    publications = Publication.objects.order_by('-date')[:MAX_NUM_PUBS]
    talks = Talk.objects.order_by('-date')[:MAX_NUM_TALKS]
    videos = Video.objects.order_by('-date')[:MAX_NUM_VIDEOS]

    # Get the most recent publication date for each project
    latest_publication_dates = Publication.objects.filter(projects=OuterRef('pk')).order_by('-date')

    # Get all projects that have at least one publication, a gallery image, and
    # are active (i.e., have no end date)
    # ordered by most recent pub date and limited to MAX_NUM_PROJECTS
    active_projects = (Project.objects.filter(publication__isnull=False, gallery_image__isnull=False, end_date__isnull=True)
                .annotate(most_recent_publication=Subquery(latest_publication_dates.values('date')[:1]))
                .order_by('-most_recent_publication', 'id').distinct())[:MAX_NUM_PROJECTS]


    context = {'banners': displayed_banners,
               'news': news_items,
               'publications': publications,
               'talks': talks,
               'videos': videos,
               'projects': active_projects,
               'debug': settings.DEBUG}
    
    # People rendering
    func_end_time = time.perf_counter()
    _logger.debug(f"Rendered views/index in {func_end_time - func_start_time:0.4f} seconds")
    context['render_time'] = func_end_time - func_start_time

    # Render is a Django shortcut (aka helper function). It combines a given template—in this case
    # index.html—with a context dictionary and returns an HttpResponse object with that rendered text.
    # See: https://docs.djangoproject.com/en/4.0/topics/http/shortcuts/#render
    return render(request, 'website/index.html', context)