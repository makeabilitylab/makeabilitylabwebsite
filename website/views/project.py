from django.conf import settings # for access to settings variables, see https://docs.djangoproject.com/en/4.0/topics/settings/#using-settings-in-python-code
from website.models import Project, Position, ProjectRole
from website.models.project_role import LeadProjectRoleTypes
from website.models.position import MemberClassification
import website.utils.ml_utils as ml_utils 
from django.shortcuts import render, get_object_or_404, redirect
from operator import attrgetter

from django.db.models import Q, F
from django.utils import timezone
from datetime import timedelta

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
    videos = project.video_set.order_by('-date')
    talks = project.talk_set.order_by('-date')
    news = project.news_set.order_by('-date')
    photos = project.photo_set.all()
    num_contributors = project.get_contributor_count()
    sponsors = project.sponsors.all()

    # Get PIs, Co-PIs, and lead graduate students for this project
    print("project.end_date", project.end_date)

    # Get current date
    current_date = timezone.now().date()

    # TODO: the logic for this needs to be updated. I think we can categorize "active_pis" if they have an
    # end_date that is less than the project end update

    # Query for active PIs. Active PIs are defined as either:
    # 1. They have an end_date that is null
    # 2. They have an end_date that is >= the current date
    # 3. They have an end_date that is >= the project end date
    # If project.end_date is None, we will not include it in the query
    buffer_days = timedelta(days=45)
    active_role_query_conditions = Q(end_date__isnull=True) | Q(end_date__gte=current_date)
    if project.end_date is not None:
        active_role_query_conditions |= Q(end_date__gte=F('project__end_date') - buffer_days)

    all_PIs = (ProjectRole.objects.filter(
            project=project,
            lead_project_role=LeadProjectRoleTypes.PI)
        .distinct('person'))
    
    print("all_PIs", all_PIs)
    
    active_PIs = (ProjectRole.objects.filter(
            active_role_query_conditions,
            project=project,
            lead_project_role=LeadProjectRoleTypes.PI)
        .distinct('person'))
    
    print("active_PIs", active_PIs)

    # Query for active Co-PIs
    active_Co_PIs = (ProjectRole.objects.filter(
            active_role_query_conditions,
            project=project,
            lead_project_role=LeadProjectRoleTypes.CO_PI)
        .distinct('person'))
    
    # All student leads
    all_student_leads = (ProjectRole.objects.filter(
            project=project,
            lead_project_role=LeadProjectRoleTypes.STUDENT_LEAD)
        .distinct('person'))
    print("all_student_leads", all_student_leads)
    
    # Query for active student leads
    active_student_leads = (ProjectRole.objects.filter(
            active_role_query_conditions,
            project=project,
            lead_project_role=LeadProjectRoleTypes.STUDENT_LEAD)
        .distinct('person'))
    print("active_student_leads", active_student_leads)

    # Query for inactive PIs
    inactive_role_query_conditions = Q(end_date__lt=current_date)
    if project.end_date is not None:
        inactive_role_query_conditions |= Q(end_date__lt=project.end_date)
    
    inactive_PIs = (ProjectRole.objects.filter(
            inactive_role_query_conditions,
            project=project,
            lead_project_role=LeadProjectRoleTypes.PI,   
        ).exclude(person__in=[role.person for role in active_PIs]).distinct('person'))

    # Query for inactive Co-PIs
    inactive_Co_PIs = (ProjectRole.objects.filter(
            inactive_role_query_conditions,
            project=project,
            lead_project_role=LeadProjectRoleTypes.CO_PI,
        ).exclude(person__in=[role.person for role in active_Co_PIs]).distinct('person'))
    
    # Query for inactive student leads
    inactive_student_leads = (ProjectRole.objects.filter(
            inactive_role_query_conditions,
            project=project,
            lead_project_role=LeadProjectRoleTypes.STUDENT_LEAD,
        ).exclude(person__in=[role.person for role in active_student_leads]).distinct('person'))

    context = {'banners': displayed_banners,
               'project': project,
               'publications': publications,
               'talks': talks,
               'videos': videos,
               'news': news,
               'photos': photos,
               'sponsors': sponsors,
               'num_contributors': num_contributors,
               'date_str' : project.get_project_dates_str(),
               'active_PIs': active_PIs,
               'active_student_leads': active_student_leads,
               'debug': settings.DEBUG}

    func_end_time = time.perf_counter()
    _logger.debug(f"Prepared '{project.name}' in {func_end_time - func_start_time:0.4f} seconds")
    context['render_time'] = func_end_time - func_start_time

    # Render is a Django helper function. It combines a given template—in this case project.html—with
    # a context dictionary and returns an HttpResponse object with that rendered text.
    # See: https://docs.djangoproject.com/en/4.0/topics/http/shortcuts/#render
    return render(request, 'website/project.html', context)