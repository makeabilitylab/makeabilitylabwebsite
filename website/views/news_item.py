from django.conf import settings # for access to settings variables, see https://docs.djangoproject.com/en/4.0/topics/settings/#using-settings-in-python-code
from website.models import News

import website.utils.ml_utils as ml_utils 
from django.shortcuts import render, get_object_or_404
from django.http import Http404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

# For logging
import time
import logging

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

MAX_RECENT_MAKEABILITY_LAB_NEWS = 3
MAX_RECENT_NEWS_ITEMS_FOR_PROJECT = 3
MAX_RECENT_NEWS_ITEMS_BY_AUTHOR = 3

def news_item(request, slug=None, id=None):
    func_start_time = time.perf_counter()

    if slug is not None:
        news = get_object_or_404(News, slug=slug)
    elif id is not None:
        news = get_object_or_404(News, id=id)
    else:
        raise Http404("No News matches the given query.")
    
    _logger.debug(f"Starting views/news for news.slug={slug} at {func_start_time:0.4f}")

    # news = get_object_or_404(News, slug=slug)
    # news = get_object_or_404(News, pk=news_id)

    recent_ml_news = News.objects.order_by('-date')[:MAX_RECENT_MAKEABILITY_LAB_NEWS]

    # max_extra_items = 4  # Maximum number of authors
    # all_author_news = news.author.news_set.order_by('-date')
    # author_news = []
    
    # for item in all_author_news:
    #     if item != news:
    #         author_news.append(item)

    # project_news = {}

    # if news.project != None:
    #     for project in news.project.all():
    #         ind_proj_news = []
    #         all_proj_news = project.news_set.order_by('-date')
    #         for item in all_proj_news:
    #             if item != news:
    #                 ind_proj_news.append(item)
    #         project_news[project] = ind_proj_news[:max_extra_items]
    print(recent_ml_news);
    context = {'news_item': news,
               'recent_ml_news': recent_ml_news,
               'navbar_white': True,
               'debug': settings.DEBUG}
    
    func_end_time = time.perf_counter()
    _logger.debug(f"Prepared views/news for news.slug={slug} in {func_end_time - func_start_time:0.4f} seconds")
    context['render_time'] = func_end_time - func_start_time

    # Render is a Django helper function. It combines a given template—in this case news.html—with
    # a context dictionary and returns an HttpResponse object with that rendered text.
    # See: https://docs.djangoproject.com/en/4.0/topics/http/shortcuts/#render
    return render(request, 'website/news_item.html', context)