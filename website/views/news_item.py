from django.conf import settings # for access to settings variables, see https://docs.djangoproject.com/en/4.0/topics/settings/#using-settings-in-python-code
from django.db.models import Prefetch # fore prefetching
from website.models import News, Project

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

    recent_ml_news = (News.objects
                        .exclude(id=news.id) # exclude the current news item
                        .order_by('-date')[:MAX_RECENT_MAKEABILITY_LAB_NEWS])

    # Define a Prefetch object for the 'project' field with a custom queryset
    # The Prefetch object in Django is used to optimize database queries when dealing with related objects. 
    # In this case, each News item has a ManyToMany relationship with Project. Without prefetching, if you were 
    # to access the related Project objects for each News item in a loop, Django would have to make a separate 
    # database query for each News item, leading to a large number of queries. This is often referred to as the “N+1 query problem”.
    prefetch = Prefetch('news_set', queryset=News.objects.exclude(id=news.id).order_by('-date'))

    # Use the prefetch_related method with the Prefetch object
    project_news_items = news.project.all().prefetch_related(prefetch)[:MAX_RECENT_NEWS_ITEMS_FOR_PROJECT]

    recent_news_posts_by_author = (news.author.news_set
                                   .exclude(id=news.id) # exclude the current news item
                                   .order_by('-date')[:MAX_RECENT_NEWS_ITEMS_BY_AUTHOR])

    print("recent_ml_news", recent_ml_news)
    print("recent_news_posts_by_author", recent_news_posts_by_author)

    context = {'news_item': news,
               'recent_ml_news': recent_ml_news,
               'project_news_items': project_news_items,
               'recent_news_posts_by_author': recent_news_posts_by_author,
               'navbar_white': True,
               'debug': settings.DEBUG}
    
    func_end_time = time.perf_counter()
    _logger.debug(f"Prepared views/news for news.slug={slug} in {func_end_time - func_start_time:0.4f} seconds")
    context['render_time'] = func_end_time - func_start_time

    # Render is a Django helper function. It combines a given template—in this case news.html—with
    # a context dictionary and returns an HttpResponse object with that rendered text.
    # See: https://docs.djangoproject.com/en/4.0/topics/http/shortcuts/#render
    return render(request, 'website/news_item.html', context)