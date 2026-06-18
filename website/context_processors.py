#!/usr/bin/env python
# -*- coding:utf-8 -*-

""" Custom context processors that allows us to pass variables to every view
    See: https://docs.djangoproject.com/en/2.0/ref/templates/api/#subclassing-context-requestcontext
         https://stackoverflow.com/questions/2893724/creating-my-own-context-processor-in-django
         https://stackoverflow.com/questions/36093221/how-to-put-variable-from-database-into-base-html-template
"""

from .models import News
from django.conf import settings
from website.utils.metadata import site_scheme as metadata_site_scheme

def recent_news(request):
    """ context processors returning recent news """
    news_items_num = 3  # Defines the number of news items that will be selected
    news_items = News.objects.order_by('-date')[:news_items_num]

    return { 'recent_news': news_items, }

def site_scheme(request):
    """
    Expose the canonical URL scheme (``http`` / ``https``) to every template, so
    templates can build absolute URLs as
    ``{{ site_scheme }}://{{ request.get_host }}{{ path }}`` that aren't ``http://``
    behind UW CSE's TLS-terminating proxy (issue #1236).

    Delegates to :func:`website.utils.metadata.site_scheme` (the single source of
    truth, keyed on ``DJANGO_ENV``) so the scheme used by view-built JSON-LD URLs
    and template-built canonical/OG URLs can't drift.
    """
    return {'site_scheme': metadata_site_scheme(request)}

def admin_version_info(request):
    """
    Make version and debug info available to all templates.
    
    This is used by the admin interface to display the current 
    website version in the header and show a debug indicator.
    
    Returns:
        dict: Context variables for ML_WEBSITE_VERSION and DEBUG.
    """
    return {
        'ML_WEBSITE_VERSION': settings.ML_WEBSITE_VERSION,
        'ML_WEBSITE_VERSION_DESCRIPTION': settings.ML_WEBSITE_VERSION_DESCRIPTION,
        'DEBUG': settings.DEBUG,
    }