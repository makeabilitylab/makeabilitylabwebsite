from django.conf import settings # for access to settings variables, see https://docs.djangoproject.com/en/4.0/topics/settings/#using-settings-in-python-code
from website.models import Publication
from django.shortcuts import render # for render https://docs.djangoproject.com/en/4.0/topics/http/shortcuts/#render
import website.utils.fileutils as ml_fileutils

# For logging
import time
import logging
import os

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

def publications(request):
    func_start_time = time.perf_counter()
    _logger.debug(f"Starting views/publications at {func_start_time:0.4f}")

    # We want all pubs after I joined as a professor. This was a group decision.
    # See https://stackoverflow.com/a/4668703
    # sampledate__gte=datetime.date(2011, 1, 1),
    # Old: Publication.objects.filter(date__range=["2012-01-01", date.today()]),
    publications = Publication.objects.filter(date__gte=settings.DATE_MAKEABILITYLAB_FORMED).order_by('-date')

    # Loop through pubs and store in a dict with year : list of pubs ordered by date
    map_year_to_pub_list = dict()
    for pub in publications:
        if pub.date.year not in map_year_to_pub_list:
            map_year_to_pub_list[pub.date.year] = list()

        map_year_to_pub_list[pub.date.year].append(pub)

        # add filename
        pub.filename_no_ext = ml_fileutils.get_filename_no_ext(pub.pdf_file.name)
        #pub.citation_bib_filename = f"{filename_no_ext}-Citation.bib"
        #pub.citation_txt_filename = f"{filename_no_ext}-Citation.txt"

    context = {'publications': publications,
               'map_year_to_pub_list': map_year_to_pub_list,
               'debug': settings.DEBUG,
               'navbar_white': True}
    
    # Render is a Django shortcut (aka helper function). It combines a given template with a 
    # context dictionary and returns an HttpResponse object with that rendered text.
    # See: https://docs.djangoproject.com/en/4.0/topics/http/shortcuts/#render
    render_func_start_time = time.perf_counter()
    render_response = render(request, 'website/publications.html', context)
    render_func_end_time = time.perf_counter()
    _logger.debug(f"Took {render_func_end_time - render_func_start_time:0.4f} seconds to create render_response")

    func_end_time = time.perf_counter()
    _logger.debug(f"Prepared {publications.count()} publications in {func_end_time - func_start_time:0.4f} seconds")
    context['render_time'] = func_end_time - func_start_time

    return render_response