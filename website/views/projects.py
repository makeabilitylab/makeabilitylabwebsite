from django.conf import settings # for access to settings variables, see https://docs.djangoproject.com/en/4.0/topics/settings/#using-settings-in-python-code
from website.models import Banner, Project
import website.utils.ml_utils as ml_utils 
from django.shortcuts import render # for render https://docs.djangoproject.com/en/4.0/topics/http/shortcuts/#render

def projects(request):
    """
    Creates the render context for the project gallery page.
    :param request:
    :return:
    """
    all_banners = Banner.objects.filter(page=Banner.PROJECTS)
    displayed_banners = ml_utils.choose_banners(all_banners)
    projects = Project.objects.all()

    # Only show projects that have a thumbnail, description, and a publication
    # we used to only filter out incomplete projects if DEBUG = TRUE; if not settings.DEBUG:
    projects = ml_utils.filter_incomplete_projects(projects)

    # if we are in debug mode, we include all projects even if they have no artifacts
    # as long as they have a start date
    ordered_projects = ml_utils.sort_projects_by_most_recent_pub(projects, settings.DEBUG)

    context = {'projects': ordered_projects,
               'banners': displayed_banners,
               'filter': filter,
               'debug': settings.DEBUG}
    
     # Render is a Django helper function. It combines a given template—in this case projects.html—with
    # a context dictionary and returns an HttpResponse object with that rendered text.
    # See: https://docs.djangoproject.com/en/4.0/topics/http/shortcuts/#render
    return render(request, 'website/projects.html', context)