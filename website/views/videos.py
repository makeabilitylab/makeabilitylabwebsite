from django.conf import settings # for access to settings variables, see https://docs.djangoproject.com/en/4.0/topics/settings/#using-settings-in-python-code
from website.models import Banner, Video
import website.utils.ml_utils as ml_utils 
from django.shortcuts import render # for render https://docs.djangoproject.com/en/4.0/topics/http/shortcuts/#render

def videos(request):
    all_banners = Banner.objects.filter(page=Banner.VIDEOS)
    displayed_banners = ml_utils.choose_banners(all_banners)
    
    # TODO: figure out what these rest commands are for
    filter = request.GET.get('filter', None)
    groupby = request.GET.get('groupby', "No-Group")

    context = {'videos': Video.objects.filter(date__gte=settings.DATE_MAKEABILITYLAB_FORMED).order_by('-date'),
               'banners': displayed_banners,
               'filter': filter,
               'groupby': groupby,
               'debug': settings.DEBUG}

    # Render is a Django helper function. It combines a given template—in this case videos.html—with
    # a context dictionary and returns an HttpResponse object with that rendered text.
    # See: https://docs.djangoproject.com/en/4.0/topics/http/shortcuts/#render
    return render(request, 'website/videos.html', context)