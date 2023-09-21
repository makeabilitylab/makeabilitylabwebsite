from django.conf import settings # for access to settings variables, see https://docs.djangoproject.com/en/4.0/topics/settings/#using-settings-in-python-code
from website.models import Banner, Publication
import website.utils.ml_utils as ml_utils 
from django.shortcuts import render # for render https://docs.djangoproject.com/en/4.0/topics/http/shortcuts/#render

import website.utils.ml_utils as ml_utils # for banner functionality

# For logging
import time
import logging

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

def publications(request):
    func_start_time = time.perf_counter()

    all_banners = Banner.objects.filter(page=Banner.PUBLICATIONS)
    displayed_banners = ml_utils.choose_banners(all_banners)
    filter = request.GET.get('filter', None)
    groupby = request.GET.get('groupby', "No-Group")

    # We want all pubs after I joined as a professor. This was a group decision.
    # See https://stackoverflow.com/a/4668703
    # sampledate__gte=datetime.date(2011, 1, 1),
    # Old: Publication.objects.filter(date__range=["2012-01-01", date.today()]),
    publications = Publication.objects.filter(date__gte=settings.DATE_MAKEABILITYLAB_FORMED)
    context = {'publications': publications,
               'banners': displayed_banners,
               'filter': filter,
               'groupby': groupby,
               'debug': settings.DEBUG}
    
    func_end_time = time.perf_counter()
    _logger.debug(f"Rendered {publications.count()} publications in {func_end_time - func_start_time:0.4f} seconds")

    # Render is a Django shortcut (aka helper function). It combines a given template with a 
    # context dictionary and returns an HttpResponse object with that rendered text.
    # See: https://docs.djangoproject.com/en/4.0/topics/http/shortcuts/#render
    return render(request, 'website/publications.html', context)