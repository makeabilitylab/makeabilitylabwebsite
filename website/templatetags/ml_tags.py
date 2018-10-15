# Read more about custom tags and filters here: https://docs.djangoproject.com/en/dev/howto/custom-template-tags/#writing-custom-template-filters
from django import template
from django.template.defaultfilters import stringfilter

from django.template.defaulttags import register

register = template.Library()

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
