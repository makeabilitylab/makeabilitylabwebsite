from django.conf import settings # for access to settings variables, see https://docs.djangoproject.com/en/4.0/topics/settings/#using-settings-in-python-code
from website.models import Banner, Position, Person
import website.utils.ml_utils as ml_utils 
import operator
from django.shortcuts import render # for render https://docs.djangoproject.com/en/4.0/topics/http/shortcuts/#render

# For logging
import time
import logging

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

def people(request):
    func_start_time = time.perf_counter()
    _logger.debug(f"Starting views/people at {func_start_time:0.4f}")

    persons = Person.objects.all()
    map_status_to_title_to_people = dict()
    map_status_to_headers = dict()
    map_header_text_to_header_name = dict()
    map_status_to_num_people = dict()

    latest_position_start_time = time.perf_counter()
    non_null_position_count = 0
    for person in persons:
        position = person.get_latest_position

        if position is not None:
            non_null_position_count = non_null_position_count + 1
            title = position.title
            if "Professor" in position.title:  # necessary to collapse all prof categories to 1
                title = "Professor"

            member_status_name = ""
            if position.is_current_member():
                member_status_name = Position.CURRENT_MEMBER
            elif position.is_alumni_member():
                member_status_name = Position.PAST_MEMBER
            elif position.is_current_collaborator():
                member_status_name = Position.CURRENT_COLLABORATOR
            elif position.is_past_collaborator():
                member_status_name = Position.PAST_COLLABORATOR

            if member_status_name not in map_status_to_title_to_people:
                map_status_to_title_to_people[member_status_name] = dict()

            if title not in map_status_to_title_to_people[member_status_name]:
                map_status_to_title_to_people[member_status_name][title] = list()

            map_status_to_title_to_people[member_status_name][title].append(position)

    latest_position_end_time = time.perf_counter()
    _logger.debug(f"Took {latest_position_end_time - latest_position_start_time:0.4f} seconds to get the latest positions for {persons.count()} people (and {non_null_position_count} had positions)")

    # now go through these dicts and sort people by dates
    sort_people_start_time = time.perf_counter()
    for status, map_title_to_people in map_status_to_title_to_people.items():
        for title, people_with_title in map_title_to_people.items():
            if "Current" in status:
                # sort current members and collaborators by start date first (so
                # people who started earliest are shown first)
                # people_with_title.sort(key=operator.attrgetter('start_date'))

                # sort people by their earliest position in the current role
                people_with_title.sort(key=lambda pos: (
                    pos.person.get_earliest_position_in_role(pos.role).start_date
                ))
            elif "Past" in status:
                # sort past members and collaborators reverse chronologically by end date (so people
                # who ended most recently are shown first)
                people_with_title.sort(key=operator.attrgetter('end_date'), reverse=True)

    sort_people_end_time = time.perf_counter()
    _logger.debug(f"Took {sort_people_end_time - sort_people_start_time:0.4f} seconds to sort people by position and date")

    position_start_time = time.perf_counter()

    # Get a list of all titles
    sorted_titles = Position.get_sorted_titles()

    # Professors can't be past members, so deal with this case
    if Position.PAST_MEMBER in map_status_to_title_to_people and \
            "Professor" in map_status_to_title_to_people[Position.PAST_MEMBER]:
        del map_status_to_title_to_people[Position.PAST_MEMBER]["Professor"]

    # to avoid getting errors when there are no people in these categories, set our defaults
    positionNames = [Position.CURRENT_MEMBER, 
                     Position.CURRENT_COLLABORATOR, 
                     Position.PAST_MEMBER,
                     Position.PAST_COLLABORATOR]

    for position in positionNames:
        map_status_to_headers[position] = dict()
        map_status_to_headers[position]["subHeader"] = "None"
        map_status_to_headers[position]["headerText"] = list()

    position_end_time = time.perf_counter()
    _logger.debug(f"Took {position_end_time - position_start_time:0.4f} seconds to tabulate position roles for {persons.count()} people")

    # setup title headers for webpage
    for status, map_title_to_people in map_status_to_title_to_people.items():
        if status not in map_status_to_headers:
            map_status_to_headers[status] = dict()

        # get the subHeaders, headerTexts, and headerNames
        map_status_to_headers[status]["subHeader"] = ""
        map_status_to_headers[status]["headerText"] = list()
        map_status_to_num_people[status] = 0

        need_comma = False
        for title in sorted_titles:
            if title in map_title_to_people and len(map_title_to_people[title]) > 0:
                if need_comma:
                    map_status_to_headers[status]["subHeader"] += ", "

                header = title + " (" + str(len(map_title_to_people[title])) + ")"
                # print(title)
                map_status_to_headers[status]["subHeader"] += header
                map_status_to_headers[status]["headerText"].append(header)
                map_header_text_to_header_name[title + " (" + str(len(map_title_to_people[title])) + ")"] = title
                map_status_to_num_people[status] += len(map_title_to_people[title])
                need_comma = True

    all_banners = Banner.objects.filter(page=Banner.PEOPLE)
    displayed_banners = ml_utils.choose_banners(all_banners)

    context = {
        'people': Person.objects.all(),
        'map_status_to_title_to_people': map_status_to_title_to_people,
        'map_status_to_num_people': map_status_to_num_people,
        'map_status_to_headers': map_status_to_headers,
        'map_header_text_to_header_name': map_header_text_to_header_name,
        'sorted_titles': sorted_titles,
        'positions': Position.objects.all(),
        'banners': displayed_banners,
        'debug': settings.DEBUG
    }

    # People rendering
    func_end_time = time.perf_counter()
    _logger.debug(f"Rendered people in {func_end_time - func_start_time:0.4f} seconds")

    # Render is a Django helper function. It combines a given template—in this case people.html—with
    # a context dictionary and returns an HttpResponse object with that rendered text.
    # See: https://docs.djangoproject.com/en/4.0/topics/http/shortcuts/#render
    return render(request, 'website/people.html', context)