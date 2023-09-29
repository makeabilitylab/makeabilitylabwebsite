# for access to settings variables, see https://docs.djangoproject.com/en/4.0/topics/settings/#using-settings-in-python-code
from django.conf import settings
from website.models import Banner
import website.utils.ml_utils as ml_utils

# for render https://docs.djangoproject.com/en/4.0/topics/http/shortcuts/#render
from django.shortcuts import render

def faq(request):
    all_banners = Banner.objects.filter(page=Banner.PEOPLE)
    displayed_banners = ml_utils.choose_banners(all_banners)
    context = {'banners': displayed_banners,
               'debug': settings.DEBUG}

    # Render is a Django helper function. It combines a given template—in this case faq.html—with
    # a context dictionary and returns an HttpResponse object with that rendered text.
    # See: https://docs.djangoproject.com/en/4.0/topics/http/shortcuts/#render
    return render(request, "website/faq.html", context)
