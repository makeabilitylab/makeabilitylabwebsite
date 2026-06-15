from django.conf import settings # for access to settings variables, see https://docs.djangoproject.com/en/4.0/topics/settings/#using-settings-in-python-code
from django.utils import timezone # for timezone-aware date operations
from website.models import Project, ProjectUmbrella, Publication
from django.db.models import Count, Q # see https://docs.djangoproject.com/en/4.2/topics/db/aggregation/
from django.db.models import OuterRef, Subquery, F
from django.shortcuts import render # for render https://docs.djangoproject.com/en/4.0/topics/http/shortcuts/#render

# For logging
import time
import logging

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

def project_listing(request):
    func_start_time = time.perf_counter()
    _logger.debug(f"Starting views/projects at {func_start_time:0.4f}")

    # Get today's date for filtering completed projects
    today = timezone.now().date()

    # Get the most recent publication date for each project
    latest_publication_dates = Publication.objects.filter(projects=OuterRef('pk')).order_by('-date')

    # Get all visible, active projects (i.e., marked is_visible and with no end
    # date OR an end date today or in the future), ordered by most recent pub
    # date. Visibility is governed solely by the is_visible flag (#1300).
    # nulls_last keeps a visible project that has no publication yet from
    # sorting to the top.
    active_projects = (Project.objects.filter(is_visible=True)
                .filter(Q(end_date__isnull=True) | Q(end_date__gt=today))
                .annotate(most_recent_publication=Subquery(latest_publication_dates.values('date')[:1]))
                .order_by(F('most_recent_publication').desc(nulls_last=True), 'id').distinct())

    # Get visible, completed projects (an end date before today),
    # ordered by most recent pub date
    completed_projects = (Project.objects.filter(is_visible=True, end_date__isnull=False, end_date__lte=today)
                .annotate(most_recent_publication=Subquery(latest_publication_dates.values('date')[:1]))
                .order_by(F('most_recent_publication').desc(nulls_last=True), 'id').distinct())
    
    # Now get all project umbrellas for interactive project filtering
    map_project_umbrella_to_projects = {}

    # Only count/list publicly-visible projects so private projects (#1300)
    # don't inflate the filter counts or leak their names into the page.
    project_umbrellas_with_projects = (ProjectUmbrella.objects.annotate(
        num_projects=Count('project', filter=Q(project__is_visible=True)))
        .filter(num_projects__gt=0)) # Get all project umbrellas with at least one visible project

    # Iterate over the queryset
    for project_umbrella in project_umbrellas_with_projects:
        # Get the list of associated, publicly-visible Project instances
        projects = project_umbrella.project_set.filter(is_visible=True)
        map_project_umbrella_to_projects[project_umbrella.short_name] = [project.name for project in projects]

    # Sort the dictionary by project count
    sorted_map_project_umbrella_to_projects = {k: v for k, v in sorted(map_project_umbrella_to_projects.items(), 
                                                                       key=lambda item: len(item[1]), reverse=True)}

    context = {'active_projects': active_projects,
               'completed_projects': completed_projects,
               'map_project_umbrella_to_projects': sorted_map_project_umbrella_to_projects,
               'debug': settings.DEBUG,
               'navbar_white': True}
     
    # Render is a Django helper function. It combines a given template—in this case projects.html—with
    # a context dictionary and returns an HttpResponse object with that rendered text.
    # See: https://docs.djangoproject.com/en/4.0/topics/http/shortcuts/#render
    render_func_start_time = time.perf_counter()
    render_response = render(request, 'website/project_listing.html', context)
    render_func_end_time = time.perf_counter()
    _logger.debug(f"Took {render_func_end_time - render_func_start_time:0.4f} seconds to create render_response")

    func_end_time = time.perf_counter()
    num_projects = len(active_projects) + len(completed_projects)
    _logger.debug(f"Prepared {num_projects} projects for views/projects in {func_end_time - func_start_time:0.4f} seconds")
    context['render_time'] = func_end_time - func_start_time

    return render_response