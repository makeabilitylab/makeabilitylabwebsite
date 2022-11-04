from django.conf import settings # for access to settings variables, see https://docs.djangoproject.com/en/4.0/topics/settings/#using-settings-in-python-code
from website.models import Project, Position
import website.utils.ml_utils as ml_utils 
from django.shortcuts import render, get_object_or_404, redirect
from operator import attrgetter
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
    :param request:
    :param project_name:
    :return:
    """
    start_time = time.perf_counter()
    project = get_object_or_404(Project, short_name__iexact=project_name)
    all_banners = project.banner_set.all()
    displayed_banners = ml_utils.choose_banners(all_banners)

    publications = project.publication_set.order_by('-date')
    videos = project.video_set.order_by('-date')
    talks = project.talk_set.order_by('-date')
    news = project.news_set.order_by('-date')
    photos = project.photo_set.all()

    start_time_position = time.perf_counter()
    
    # A Project_Role object has a person, role (open text field), start_date, end_date
    project_roles = project.projectrole_set.order_by('start_date')

    # Sort project roles by start date and then title (e.g., professors first) and then last name
    project_roles = sorted(project_roles, key=lambda pr: (pr.start_date, pr.get_pi_status_index(), pr.person.get_current_title_index(), pr.person.last_name))

    project_roles_current = []
    project_roles_past = []

    for project_role in project_roles:
        if project_role.is_active():
            project_roles_current.append(project_role)
        elif project_role.has_completed_role():
            project_roles_past.append(project_role)

    _logger.warn("project_roles_past: ", project_roles_past)
    project_roles_past = [] # sorted(project_roles_past, key=attrgetter('end_date'), reverse=True)

    map_status_to_title_to_project_role = dict()

    for project_role in project_roles:
        person = project_role.person

        position = person.get_latest_position()
        if position is not None:
            title = position.title
            if "Professor" in position.title:  # necessary to collapse all prof categories to 1
                title = "Professor"

            # check for current status on project
            member_status_name = "unknown"
            if project_role.is_active():
                member_status_name = Position.CURRENT_MEMBER
            elif project_role.has_completed_role():
                member_status_name = Position.PAST_MEMBER
            elif project_role.has_role_started():
                member_status_name = Position.FUTURE_MEMBER

            if member_status_name not in map_status_to_title_to_project_role:
                map_status_to_title_to_project_role[member_status_name] = dict()

            if title not in map_status_to_title_to_project_role[member_status_name]:
                map_status_to_title_to_project_role[member_status_name][title] = list()

            map_status_to_title_to_project_role[member_status_name][title].append(project_role)

    for status, map_title_to_project_role in map_status_to_title_to_project_role.items():
        for title, project_role_with_title in map_title_to_project_role.items():
            if "Current" in status:
                # sort current members and collaborators by start date first (so
                # people who started earliest are shown first)
                project_role_with_title.sort(key=attrgetter('start_date'))
            elif "Past" in status:
                # sort past members and collaborators reverse chronologically by end date (so people
                # who ended most recently are shown first)
                project_role_with_title.sort(key=attrgetter('end_date'), reverse=True)

    # TODO: While we likely want current members sorted by titles, I think it makes the most sense
    #       to sort previous members by most recent first (and ignore title)... but I'm not sure
    sorted_titles = Position.get_sorted_titles()

    map_status_to_title_to_people = map_status_to_title_to_project_role
    end_time_position = time.perf_counter()
    _logger.debug(f"Took {end_time_position - start_time_position:0.4f} seconds to calculate position roles for '{project.name}'")

    context = {'banners': displayed_banners,
               'project': project,
               'project_roles': project_roles,
               'project_roles_current': project_roles_current,
               'project_roles_past': project_roles_past,
               'map_status_to_title_to_project_role': map_status_to_title_to_project_role,
               'map_status_to_title_to_people': map_status_to_title_to_people,
               'sorted_titles': sorted_titles,
               'publications': publications,
               'talks': talks,
               'videos': videos,
               'news': news,
               'photos': photos,
               'debug': settings.DEBUG}

    end_time = time.perf_counter()
    _logger.debug(f"Rendered '{project.name}' in {end_time - start_time:0.4f} seconds")

    # Render is a Django helper function. It combines a given template—in this case project.html—with
    # a context dictionary and returns an HttpResponse object with that rendered text.
    # See: https://docs.djangoproject.com/en/4.0/topics/http/shortcuts/#render
    return render(request, 'website/project.html', context)