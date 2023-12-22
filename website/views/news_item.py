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
MAX_RECENT_NEWS_ITEMS_ABOUT_PEOPLE_MENTIONED = 3

def news_item(request, slug=None, id=None):
    func_start_time = time.perf_counter()

    if slug is not None:
        cur_news_item = get_object_or_404(News, slug=slug)
    elif id is not None:
        cur_news_item = get_object_or_404(News, id=id)
    else:
        raise Http404("No News matches the given query.")
    
    _logger.debug(f"Starting views/news for news.slug={slug} at {func_start_time:0.4f}")

    # news = get_object_or_404(News, slug=slug)
    # news = get_object_or_404(News, pk=news_id)

    recent_ml_news = (News.objects
                        .exclude(id=cur_news_item.id) # exclude the current news item
                        .order_by('-date')[:MAX_RECENT_MAKEABILITY_LAB_NEWS])


    excluded_ids = list(recent_ml_news.values_list('id', flat=True))
    related_projects = cur_news_item.project.all()
    recent_news_about_projects_mentioned = (News.objects
                                   .exclude(id=cur_news_item.id) # exclude the current news item
                                   .exclude(id__in=excluded_ids) # don't want to repeat
                                   .filter(project__in=related_projects)
                                   .order_by('-date').distinct()[:MAX_RECENT_NEWS_ITEMS_BY_AUTHOR])
    
    
    # Combine the IDs from recent_ml_news and recent_news_about_projects_mentioned
    excluded_ids.extend(list(recent_news_about_projects_mentioned.values_list('id', flat=True)))
    
    people_mentioned = cur_news_item.people.all()
    recent_news_about_people_mentioned = (News.objects
                                          .exclude(id=cur_news_item.id)
                                          .exclude(id__in=excluded_ids)
                                          .filter(people__in=people_mentioned)
                                          .order_by('-date').distinct()[:MAX_RECENT_NEWS_ITEMS_ABOUT_PEOPLE_MENTIONED])

    excluded_ids.extend(list(recent_news_about_people_mentioned.values_list('id', flat=True)))
    recent_news_posts_by_author = (cur_news_item.author.authored_news
                                   .exclude(id=cur_news_item.id) # exclude the current news item
                                   .exclude(id__in=excluded_ids)
                                   .order_by('-date')[:MAX_RECENT_NEWS_ITEMS_BY_AUTHOR])
    
    
    context = {'news_item': cur_news_item,
               'people_mentioned': people_mentioned,
               'related_projects': related_projects,
               'recent_ml_news': recent_ml_news,
               'recent_news_about_projects_mentioned': recent_news_about_projects_mentioned,
               'recent_news_about_people_mentioned': recent_news_about_people_mentioned,
               'recent_news_posts_by_author': recent_news_posts_by_author,
               'navbar_white': True,
               'debug': settings.DEBUG}
    
    

    # Render is a Django helper function. It combines a given template—in this case news.html—with
    # a context dictionary and returns an HttpResponse object with that rendered text.
    # See: https://docs.djangoproject.com/en/4.0/topics/http/shortcuts/#render
    render_func_start_time = time.perf_counter()
    render_response = render(request, 'website/news_item.html', context)
    render_func_end_time = time.perf_counter()
    _logger.debug(f"Took {render_func_end_time - render_func_start_time:0.4f} seconds to create render_response")

    func_end_time = time.perf_counter()
    _logger.debug(f"Prepared views/news for news.slug={slug} in {func_end_time - func_start_time:0.4f} seconds")
    context['render_time'] = func_end_time - func_start_time