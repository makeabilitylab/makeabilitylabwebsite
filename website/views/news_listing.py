from django.conf import settings # for access to settings variables, see https://docs.djangoproject.com/en/4.0/topics/settings/#using-settings-in-python-code
from website.models import Banner, News
import datetime
import website.utils.ml_utils as ml_utils 
from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

# For logging
import time
import logging

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

def news_listing(request):
    """The news listing page. This page lists all news items in reverse chronological order."""

    func_start_time = time.perf_counter()
    _logger.debug(f"Starting views/news_listing at {func_start_time:0.4f}")
    
    news_list = News.objects.all()

    # start the paginator on the first page
    page = request.GET.get('page', 1)

    # change the int parameter below to control the amount of objects displayed on a page
    paginator = Paginator(news_list, 12)
    try:
        news = paginator.page(page)
    except PageNotAnInteger:
        news = paginator.page(1)
    except EmptyPage:
        news = paginator.page(paginator.num_pages)

    context = {'news': news,
               'debug': settings.DEBUG,
               'navbar_white': True}
    
    

    # Render is a Django helper function. It combines a given template—in this case news-listing.html—with
    # a context dictionary and returns an HttpResponse object with that rendered text.
    # See: https://docs.djangoproject.com/en/4.0/topics/http/shortcuts/#render
    render_func_start_time = time.perf_counter()
    render_response = render(request, 'website/news_listing.html', context)
    render_func_end_time = time.perf_counter()
    _logger.debug(f"Took {render_func_end_time - render_func_start_time:0.4f} seconds to create render_response")

    func_end_time = time.perf_counter()
    _logger.debug(f"Prepared views/news_listing in {func_end_time - func_start_time:0.4f} seconds")
    context['render_time'] = func_end_time - func_start_time

    return render_response