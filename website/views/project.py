from django.conf import settings # for access to settings variables, see https://docs.djangoproject.com/en/4.0/topics/settings/#using-settings-in-python-code
from website.models import Project, Position, ProjectRole, Grant
from website.models.project_role import LeadProjectRoleTypes
from website.models.position import MemberClassification
import website.utils.ml_utils as ml_utils 
from django.shortcuts import render, get_object_or_404, redirect
from operator import attrgetter
from django.template.loader import render_to_string
from django.http import HttpResponse

from django.db.models import Q, F

# For logging
import time
import logging


# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

def redirect_project(request, project_name):
    """
    Redirects the project to a url with /project/
    """
    response = redirect('/project/' + project_name)
    return response

def project(request, project_name):
    """
    This is the view for *individual* project pages rather than the project page gallery
    """
    func_start_time = time.perf_counter()
    _logger.debug(f"Starting views/project {project_name} at {func_start_time:0.4f}")

    project = get_object_or_404(Project, short_name__iexact=project_name)
    all_banners = project.banner_set.all()
    displayed_banners = ml_utils.choose_banners(all_banners)

    publications = project.publication_set.order_by('-date')
    videos = project.videos.order_by('-date')
    talks = project.talk_set.order_by('-date')
    news = project.news_set.order_by('-date')
    photos = project.photo_set.all()
    num_contributors = project.get_contributor_count()
    sponsors = project.get_sponsors()
    code_repo_url = project.get_featured_code_repo_url()
    featured_video = project.get_featured_video()
    has_videos_beyond_featured_video = (project.videos.exclude(id=featured_video.id).exists() 
        if featured_video else project.videos.exists())

    _logger.debug(f"Project sponsorship: {sponsors}")
    _logger.debug(f"Project grants: {Grant.objects.filter(projects__in=[project])}")
    _logger.debug(f"The featured video: {featured_video}. Has videos beyond featured? {has_videos_beyond_featured_video}")
    _logger.debug(f"The project start date: {project.start_date} and end date: {project.end_date}")
    
    # Get PIs, Co-PIs, and lead graduate students for this project
    project_leadership = project.get_project_leadership()
    _logger.debug(f"The project leadership for {project_name}: {project_leadership}")

    # Query for related projects. Limit to top 5
    related_projects = project.get_related_projects_by_umbrella(match_all_umbrellas=True)[:5]

    # related_projects_by_pub = project.get_related_projects_by_pub()
    # _logger.debug(f"Related projects by publication: {related_projects_by_pub}")

    context = {'banners': displayed_banners,
               'project': project,
               'publications': publications,
               'talks': talks,
               'videos': videos,
               'news': news,
               'photos': photos,
               'sponsors': sponsors,
               'code_repo_url': code_repo_url,
               'featured_video': featured_video,
               'website': project.website,
               'data_url': project.data_url,
               'num_contributors': num_contributors,
               'date_str' : project.get_project_dates_str(),
               'active_PIs': project_leadership['active_PIs'],
               'active_Co_PIs': project_leadership['active_Co_PIs'],
               'active_student_leads': project_leadership["active_student_leads"],
               'active_postdoc_leads': project_leadership["active_postdoc_leads"],
               'active_research_scientist_leads': project_leadership["active_research_scientist_leads"],
               'related_projects': related_projects,
               'has_videos_beyond_featured_video': has_videos_beyond_featured_video,
               'debug': settings.DEBUG}

    context['view_prep_time'] = time.perf_counter() - func_start_time
    _logger.debug(f"Setup view for '{project.name}' (sans render) in {context['view_prep_time']:0.4f} seconds")

    # Render is a Django helper function. It combines a given template—in this case project.html—with
    # a context dictionary and returns an HttpResponse object with that rendered text.
    # See: https://docs.djangoproject.com/en/4.0/topics/http/shortcuts/#render
    render_response = render(request, 'website/project.html', context)

    func_end_time = time.perf_counter()
    _logger.debug(f"Prepared '{project.name}' in {func_end_time - func_start_time:0.4f} seconds")

    return render_response