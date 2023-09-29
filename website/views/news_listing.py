from django.conf import settings # for access to settings variables, see https://docs.djangoproject.com/en/4.0/topics/settings/#using-settings-in-python-code
from website.models import Banner, News
import datetime
import website.utils.ml_utils as ml_utils 
from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils.timezone import utc

# For logging
import time
import logging

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

# This method and the news functionality in general was written by Johnson Kuang
def news_listing(request):
    func_start_time = time.perf_counter()
    _logger.debug(f"Starting views/news_listing at {func_start_time:0.4f}")

    all_banners = Banner.objects.filter(page=Banner.FRONTPAGE)
    displayed_banners = ml_utils.choose_banners(all_banners)
    
    # TODO: investigate why we are using REST variables here
    filter = request.GET.get('filter', None)
    groupby = request.GET.get('groupby', "No-Group")
    
    now = datetime.datetime.utcnow().replace(tzinfo=utc)
    news_list = News.objects.all()

    # start the paginator on the first page
    page = request.GET.get('page', 1)

    # change the int parameter below to control the amount of objects displayed on a page
    paginator = Paginator(news_list, 10)
    try:
        news = paginator.page(page)
    except PageNotAnInteger:
        news = paginator.page(1)
    except EmptyPage:
        news = paginator.page(paginator.num_pages)

    context = {'news': news,
               'banners': displayed_banners,
               'filter': filter,
               'groupby': groupby,
               'time_now': now,
               'debug': settings.DEBUG}
    
    func_end_time = time.perf_counter()
    _logger.debug(f"Rendered views/news_listing in {func_end_time - func_start_time:0.4f} seconds")
    context['render_time'] = func_end_time - func_start_time

    # Render is a Django helper function. It combines a given template—in this case news-listing.html—with
    # a context dictionary and returns an HttpResponse object with that rendered text.
    # See: https://docs.djangoproject.com/en/4.0/topics/http/shortcuts/#render
    return render(request, 'website/news-listing.html', context)