#!/usr/bin/env python
# -*- coding:utf-8 -*-

""" Custom context processors that allows us to pass variables to every view
    See: https://docs.djangoproject.com/en/2.0/ref/templates/api/#subclassing-context-requestcontext
         https://stackoverflow.com/questions/2893724/creating-my-own-context-processor-in-django
         https://stackoverflow.com/questions/36093221/how-to-put-variable-from-database-into-base-html-template
"""

from .models import News

def recent_news(request):
    """ context processors returning recent news """
    news_items_num = 3  # Defines the number of news items that will be selected
    news_items = News.objects.order_by('-date')[:news_items_num]

    return { 'recent_news': news_items, }