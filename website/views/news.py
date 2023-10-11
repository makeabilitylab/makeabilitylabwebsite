from django.conf import settings # for access to settings variables, see https://docs.djangoproject.com/en/4.0/topics/settings/#using-settings-in-python-code
from website.models import Banner, News

import website.utils.ml_utils as ml_utils 
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

# For logging
import time
import logging

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

# This method and the news functionality in general was written by Johnson Kuang
def news(request, news_id):
    func_start_time = time.perf_counter()
    _logger.debug(f"Starting views/news for news_id={news_id} at {func_start_time:0.4f}")

    all_banners = Banner.objects.filter(page=Banner.NEWSLISTING)
    displayed_banners = ml_utils.choose_banners(all_banners)
    news = get_object_or_404(News, pk=news_id)

    max_extra_items = 4  # Maximum number of authors
    all_author_news = news.author.news_set.order_by('-date')
    author_news = []
    
    for item in all_author_news:
        if item != news:
            author_news.append(item)

    project_news = {}

    if news.project != None:
        for project in news.project.all():
            ind_proj_news = []
            all_proj_news = project.news_set.order_by('-date')
            for item in all_proj_news:
                if item != news:
                    ind_proj_news.append(item)
            project_news[project] = ind_proj_news[:max_extra_items]

    context = {'banners': displayed_banners,
               'news': news,
               'author_news': author_news[:max_extra_items],
               'project_news': project_news,
               'navbar_white': True,
               'debug': settings.DEBUG}
    
    func_end_time = time.perf_counter()
    _logger.debug(f"Rendered views/news for news_id={news_id} in {func_end_time - func_start_time:0.4f} seconds")
    context['render_time'] = func_end_time - func_start_time

    # Render is a Django helper function. It combines a given template—in this case news.html—with
    # a context dictionary and returns an HttpResponse object with that rendered text.
    # See: https://docs.djangoproject.com/en/4.0/topics/http/shortcuts/#render
    return render(request, 'website/news.html', context)