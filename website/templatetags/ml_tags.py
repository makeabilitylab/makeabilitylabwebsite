# Read more about custom tags and filters here: https://docs.djangoproject.com/en/dev/howto/custom-template-tags/#writing-custom-template-filters
from django import template
from django.template.defaulttags import register

register = template.Library()

# From https://stackoverflow.com/questions/8000022/django-template-how-to-look-up-a-dictionary-value-with-a-variable
@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)
