# Read more about custom tags and filters here: https://docs.djangoproject.com/en/dev/howto/custom-template-tags/#writing-custom-template-filters
from django import template
from django.template.defaultfilters import stringfilter
from django.conf import settings # so that get_settings_value works
import re

from django.template.defaulttags import register

from website.models import Artifact

import logging

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

register = template.Library()

# Convenience method to help return a settings variable in a template
# From: https://stackoverflow.com/a/7716141/388117
@register.simple_tag
def get_settings_value(name):
    return getattr(settings, name, "")

# This helps remove the "KeyError" from our log files when there is no variable in the template
# context. For example, we use to look for `page_title` and by {% if page_title %} but
# if page_title didn't exist, it would create a log entry
# See: https://stackoverflow.com/a/65709948
@register.simple_tag(takes_context=True)
def var_exists(context, var_name):
    dicts = context.dicts  # array of dicts
    if dicts:
        for d in dicts:
            if var_name in d:
                return True
    return False

# We use this to generate citation filenames dynamically when downloading citations like .bib
@register.simple_tag
def get_pub_filename(pub, file_extension, max_pub_title_length):
    _logger.debug(f"Started get_pub_filename: pub={pub}, file_extension={file_extension}, max_pub_title_length={max_pub_title_length}")
    generated_file_name = Artifact.generate_filename(pub, file_extension, max_pub_title_length)
    _logger.debug(f"The generated_file_name={generated_file_name}")
    return generated_file_name

# From https://stackoverflow.com/questions/8000022/django-template-how-to-look-up-a-dictionary-value-with-a-variable
@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
@stringfilter
def get_url_page(url):
    return url.split('/')[-2]

@register.filter(name='jsdate')
def jsdate(d):
    """formats a python date into a js Date() constructor.
    """
    try:
        return "new Date({0},{1},{2})".format(d.year, d.month - 1, d.day)
    except AttributeError:
        return 'undefined'

 # Removes any HTML tags in String and returns new String
@register.filter(name='removehtmltags')
@stringfilter
def removehtmltags(value):
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', value)
    return cleantext

@register.filter(name='parametric_slice')
def parametric_slice(list, cnt):
    return list[:cnt]

@register.filter(name='news_slice')
def news_slice(list, pub_cnt):
    """Returns the number of news items based on num of pubs"""
    return list[:pub_cnt + 1]

