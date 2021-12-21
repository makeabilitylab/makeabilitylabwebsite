"""
Hosts general utility functions for Makeability Lab Django website
"""

import datetime
import random 
from django.conf import settings # for access to settings variables, see https://docs.djangoproject.com/en/4.0/topics/settings/#using-settings-in-python-code
from operator import itemgetter

def get_video_embed(video_url):
    """Returns proper embed code for a video url"""

    if 'youtu.be' in video_url or 'youtube.com' in video_url:
        # https://youtu.be/i0IDbHGir-8 or https://www.youtube.com/watch?v=i0IDbHGir-8

        base_url = "https://youtube.com/embed"
        unique_url = video_url[video_url.find("/", 9):]

        # See https://developers.google.com/youtube/youtube_player_demo for details on parameterizing YouTube video
        return base_url + unique_url + "?showinfo=0&iv_load_policy=3"
    elif 'vimeo' in video_url:
        # https://player.vimeo.com/video/164630179
        vimeo_video_id = video_url.rsplit('/', 1)[-1]
        return "https://player.vimeo.com/video/" + vimeo_video_id
    else:
        return "unknown video service for '{}'".format(video_url)


def filter_incomplete_projects(projects):
    '''
    Filters out projects that don't have thumbnails, publications, an about information
    :param projects:
    :return:
    '''
    filtered = list()
    for project in projects:
        # I tested this and if project.about or project.gallery_image are not set,
        # they will be interpreted as False by Python
        if project.has_publication() and project.about and project.gallery_image:
            filtered.append(project)

    return filtered

def sort_projects_by_most_recent_pub(projects, include_projects_with_no_artifacts=False):
    return sort_projects_by_most_recent_artifact(projects, include_projects_with_no_artifacts,
                                                 only_look_at_pubs=True)

def sort_projects_by_most_recent_artifact(projects, include_projects_with_no_artifacts=False,
                                          only_look_at_pubs=True):
    """Sorts projects by most recent artifact
    :return: a sorted list of projects by most recent artifact date"""
    # print(projects)
    sorted_projects = list()
    for project in projects:

        # most_recent_artifact is a tuple of (date, artifact)
        most_recent_artifact = project.get_most_recent_artifact()

        # get most recent pub. use this instead
        if only_look_at_pubs:
            most_recent_pub = project.get_most_recent_publication()
            if most_recent_pub is not None:
                most_recent_artifact = (most_recent_pub.date, most_recent_pub)
            else:
                most_recent_artifact = None

        # _logger.debug("The most recent artifact: ", str(most_recent_artifact))
        if most_recent_artifact is not None:
            project_date_tuple = (project, most_recent_artifact[0])
            sorted_projects.append(project_date_tuple)
        elif include_projects_with_no_artifacts and project.start_date is not None:
            sorted_projects.append((project, project.start_date))

    # sort the artifacts by date
    sorted_projects = sorted(sorted_projects, key=itemgetter(1), reverse=True)

    ordered_projects = []
    if len(sorted_projects) > 0:
        ordered_projects, temp = zip(*sorted_projects)

    return ordered_projects

##### BANNER HELPER FUNCTIONS ######
# All of these functions were written by Lee Stearns
def weighted_choice(choices):
    total = sum(w for c, w in choices)
    r = random.uniform(0, total)
    upto = 0
    for c, w in choices:
        if upto + w >= r:
            return c
        upto += w
    # assert False, "Shouldn't get here"
    return choices[0][0]

def choose_banners_helper(banners, count):
    banner_weights = []
    total_weight = 0
    for banner in banners:
        elapsed = (datetime.datetime.now().date() - banner.date_added).days / 31.0
        if elapsed <= 0:
            elapsed = 1.0 / 31.0
        weight = 1.0 + 1.0 / elapsed
        banner_weights.append((banner, weight))
        total_weight += weight
    for i in range(0, len(banner_weights)):
        banner_weights[i] = (banner_weights[i][0], banner_weights[i][1] / total_weight)
        print(banner_weights[i][1])

    selected_banners = []
    for i in range(0, count):
        if len(selected_banners) == len(banners):
            break
        banner = weighted_choice(banner_weights)
        selected_banners.append(banner)
        index = [y[0] for y in banner_weights].index(banner)
        total_weight -= banner_weights[index][1]
        del banner_weights[index]
        if len(banner_weights) == 0:
            break
        for i in range(0, len(banner_weights)):
            banner_weights[i] = (banner_weights[i][0], banner_weights[i][1] / total_weight)

    return selected_banners


def choose_banners(banners):
    favorite_banners = []
    other_banners = []
    for banner in banners:
        if banner.favorite == True:
            favorite_banners.append(banner)
        else:
            other_banners.append(banner)

    selected_banners = choose_banners_helper(favorite_banners, settings.MAX_BANNERS)
    if len(selected_banners) < settings.MAX_BANNERS:
        temp = choose_banners_helper(other_banners, settings.MAX_BANNERS - len(selected_banners))
        for banner in temp:
            selected_banners.append(banner)

    return selected_banners