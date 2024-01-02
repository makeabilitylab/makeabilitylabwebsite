from django.conf import settings # for access to settings variables, see https://docs.djangoproject.com/en/4.0/topics/settings/#using-settings-in-python-code
from website.models import Banner, Publication, Talk, Video, Project, Person, News, Sponsor
import website.utils.ml_utils as ml_utils 
from django.shortcuts import render # for render https://docs.djangoproject.com/en/4.0/topics/http/shortcuts/#render
from django.db.models import OuterRef, Subquery

from django.db.models import Sum # for summing grant funding amounts
from django.db.models.functions import Coalesce # for replacing None with 0 when summing grant funding amounts

# For logging
import time
import logging
import random

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

    # Get all banners for the landing page
    banners = get_landing_page_banners(6) #Banner.objects.filter(landing_page=True)

    # TODO: update how we choose banners using Django ORM vs. python
    #displayed_banners = ml_utils.choose_banners(all_banners)

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

    # Get all sponsors, annotate each with the sum of their grants' funding_amount
    # In this code, Coalesce(Sum('grant__funding_amount'), 0) calculates the sum of the 
    # funding_amount for all grants related to each sponsor, and replaces None with 0 if 
    # there are no related grants.
    sponsors = Sponsor.objects.annotate(total_funding=Coalesce(Sum('grant__funding_amount'), 0))

    # Sort by total_funding in descending order, then by name in ascending order
    sponsors = sponsors.order_by('-total_funding', 'name')

    context = {'banners': banners,
               'news': news_items,
               'publications': publications,
               'talks': talks,
               'videos': videos,
               'projects': active_projects,
               'sponsors': sponsors,
               'debug': settings.DEBUG}
    
    # Render is a Django shortcut (aka helper function). It combines a given template—in this case
    # index.html—with a context dictionary and returns an HttpResponse object with that rendered text.
    # See: https://docs.djangoproject.com/en/4.0/topics/http/shortcuts/#render 
    render_func_start_time = time.perf_counter()
    render_response = render(request, 'website/index.html', context)
    render_func_end_time = time.perf_counter()
    _logger.debug(f"Took {render_func_end_time - render_func_start_time:0.4f} seconds to create render_response")

    # People rendering
    func_end_time = time.perf_counter()
    _logger.debug(f"Prepared views/index in {func_end_time - func_start_time:0.4f} seconds")
    context['render_time'] = func_end_time - func_start_time

    return render_response

def get_landing_page_banners(max_num_banners=5):
    # Get favorite banners that should appear on the landing page. Order by recency.
    # The "?" allows us to randomize the order of banners added on the same day
    fav_banners = list(Banner.objects.filter(favorite=True, landing_page=True).order_by('-date_added'))
    random.shuffle(fav_banners)
    banners = fav_banners[:max_num_banners]
    
    if len(banners) < max_num_banners:
        other_banners = list(Banner.objects.filter(landing_page=True)
                        .exclude(id__in=[b.id for b in banners]) # exclude banners in original list
                        .order_by('-date_added', '?')[:max_num_banners-len(banners)])
        random.shuffle(other_banners)
        banners += other_banners;
    
    return banners