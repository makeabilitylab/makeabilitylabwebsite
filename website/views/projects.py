from django.conf import settings # for access to settings variables, see https://docs.djangoproject.com/en/4.0/topics/settings/#using-settings-in-python-code
from website.models import Banner, Project, ProjectUmbrella
from django.db.models import Count # for Count https://docs.djangoproject.com/en/4.2/topics/db/aggregation/
from django.shortcuts import render # for render https://docs.djangoproject.com/en/4.0/topics/http/shortcuts/#render

# For logging
import time
import logging

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

def projects(request):
    """
    Creates the render context for the project gallery page.
    :param request:
    :return:
    """
    func_start_time = time.perf_counter()
    _logger.debug(f"Starting views/projects at {func_start_time:0.4f}")

    # Get all projects that have at least one publication, a gallery image, and
    # are active (i.e., have no end date)
    # ordered by most recent pub date
    active_projects = (Project.objects.filter(publication__isnull=False, gallery_image__isnull=False, end_date__isnull=True)
                # .order_by('-start_date') # this would sort by start date, but we want to sort by most recent publication
                .order_by('id', '-publication__date')
                .distinct('id'))
    
    # Get completed projects that have at least one publication, a gallery image, and
    completed_projects = (Project.objects.filter(publication__isnull=False, gallery_image__isnull=False, end_date__isnull=False)
                .order_by('id', '-publication__date')
                .distinct('id'))
    
    # Now get all project umbrellas for interactive project filtering
    map_projectumbrella_to_projects = {}

    project_umbrellas_with_projects = (ProjectUmbrella.objects.annotate(
        num_projects=Count('project')).filter(num_projects__gt=0)) # Get all project umbrellas with at least one project

    # Iterate over the queryset
    for project_umbrella in project_umbrellas_with_projects:
        # Get the list of associated Project instances
        projects = project_umbrella.project_set.all()
        map_projectumbrella_to_projects[project_umbrella.short_name] = [project.name for project in projects]


    context = {'active_projects': active_projects,
               'completed_projects': completed_projects,
               'map_projectumbrella_to_projects': map_projectumbrella_to_projects,
               'debug': settings.DEBUG,
               'navbar_white': True}
    
    func_end_time = time.perf_counter()
    num_projects = len(active_projects) + len(completed_projects)
    _logger.debug(f"Rendered {num_projects} projects for views/projects in {func_end_time - func_start_time:0.4f} seconds")
    context['render_time'] = func_end_time - func_start_time
    
    # Render is a Django helper function. It combines a given template—in this case projects.html—with
    # a context dictionary and returns an HttpResponse object with that rendered text.
    # See: https://docs.djangoproject.com/en/4.0/topics/http/shortcuts/#render
    return render(request, 'website/projects.html', context)