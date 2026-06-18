#!/usr/bin/env python
# -*- coding:utf-8 -*-

""" Custom context processors that allows us to pass variables to every view
    See: https://docs.djangoproject.com/en/2.0/ref/templates/api/#subclassing-context-requestcontext
         https://stackoverflow.com/questions/2893724/creating-my-own-context-processor-in-django
         https://stackoverflow.com/questions/36093221/how-to-put-variable-from-database-into-base-html-template
"""

from .models import News
from django.conf import settings

def recent_news(request):
    """ context processors returning recent news """
    news_items_num = 3  # Defines the number of news items that will be selected
    news_items = News.objects.order_by('-date')[:news_items_num]

    return { 'recent_news': news_items, }

def site_scheme(request):
    """
    Expose the canonical URL scheme (``http`` / ``https``) to every template.

    The site runs behind UW CSE's Apache TLS-terminating proxy, which talks to
    the Django container over plain HTTP. Because ``SECURE_PROXY_SSL_HEADER`` is
    not (yet) configured, ``request.scheme`` reports ``http`` in production/test
    even though visitors arrive over HTTPS. Building absolute URLs (canonical,
    Open Graph ``og:url``/``og:image``, Twitter Card images) from
    ``request.scheme`` therefore advertises ``http://`` links to crawlers and
    social scrapers — the root cause of issue #1236.

    This processor pins the scheme to ``https`` whenever the site is not in
    DEBUG (i.e. on the test/prod servers), while leaving local dev on whatever
    ``request.scheme`` reports (``http`` over localhost). Templates should build
    absolute URLs as ``{{ site_scheme }}://{{ request.get_host }}{{ path }}``.

    NOTE: This is the in-repo workaround. The cleaner long-term fix is for IT to
    set ``SECURE_PROXY_SSL_HEADER`` on the proxy (tracked in #1329); once that
    lands, ``request.scheme`` will be correct and this can fall back to it.
    """
    return {
        'site_scheme': request.scheme if settings.DEBUG else 'https',
    }

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