from django.conf import settings # for access to settings variables, see https://docs.djangoproject.com/en/4.0/topics/settings/#using-settings-in-python-code
from website.models import Banner, Position, Person, Publication
from website.models.position import Role
from website.models.publication import PubType
import website.utils.ml_utils as ml_utils 
import operator
from django.shortcuts import render # for render https://docs.djangoproject.com/en/4.0/topics/http/shortcuts/#render

from django.db.models import Q # allow for complex queries, see: http://docs.djangoproject.com/en/4.2/topics/db/queries/#complex-lookups-with-q-objects
from django.db.models import Count # allows us to run aggregation methods with Django, see https://docs.djangoproject.com/en/4.2/topics/db/aggregation/
from django.db.models import Case, When # allows us to custom Case and When conditionals

from datetime import date

# For logging
import time
import logging

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

def people(request):
    func_start_time = time.perf_counter()
    _logger.debug(f"Starting views/people at {func_start_time:0.4f}")

    # In Django, keyword objects are AND'ed together. If we want more complex queries (e.g,. with OR statements),
    # we need to use Q objects. See: https://docs.djangoproject.com/en/4.2/topics/db/queries/#complex-lookups-with-q-objects
    # We want to get all current members ordered by start date (ascending)
    # I'm putting this whole thing in parans, so I can comment each line, see: https://stackoverflow.com/a/67912159/388117
    # current_member_positions = (Position.objects.filter(Q(start_date__lte=date.today()), # start date is in the past
    #                         Q(end_date__isnull=True) | Q(end_date__gte=date.today()), # end date is in the future or null
    #                         Q(role=Position.MEMBER)) # must be a member of the lab
    #                         .distinct('person__id', 'start_date') # don't repeat people
    #                         .order_by('person__id', 'start_date')) # orderby must include same fields as distinct in Django
    
    map_title_to_order = Position.get_map_title_to_order();
    current_member_positions = (Position.objects.filter(Q(start_date__lte=date.today()), # start date is in the past
                            Q(end_date__isnull=True) | Q(end_date__gte=date.today()), # end date is in the future or null
                            Q(role=Role.MEMBER)) # must be a member of the lab
                            .order_by( # Order by title (in specified order) followed by start date
                               Case(*[When(title=title, then=priority_order) for (title, priority_order) in map_title_to_order.items()]),
                               'start_date' 
                            ))

    # I believe in Django, the pk and id fields are the same
    exclude_member_ids = []
    for current_member_position in current_member_positions:
        exclude_member_ids.append(current_member_position.person.id)

    current_member_position_ids = []
    for current_member_position in current_member_positions:
        current_member_position_ids.append(current_member_position.pk)
    
    # Get PHD students with dissertations
    dissertations = Publication.objects.filter(pub_venue_type=PubType.PHD_DISSERTATION).order_by('-date')
    list_of_graduated_phd_students = []
    for dissertation in dissertations:
        grad_student = dissertation.get_person()
        list_of_graduated_phd_students.append(grad_student)
        exclude_member_ids.append(grad_student.id)

    _logger.debug("exclude_member_ids", exclude_member_ids)
    
    # Get past members
    past_member_positions = (Position.objects.filter(Q(start_date__lte=date.today()), # start date is in the past
                            Q(end_date__isnull=False) | Q(end_date__lt=date.today()), # end date is not null
                            Q(role=Role.MEMBER)) # must be a member of the lab
                            .exclude(person__id__in=exclude_member_ids) # exclude current members and graduated phd students
                            .annotate(total=Count('title')).order_by('-end_date'))

    # Setup past members by title
    map_title_to_past_member_positions = {}
    for past_member_position in past_member_positions:
        abstracted_title = Position.get_abstracted_title(past_member_position.title)
        if abstracted_title not in map_title_to_past_member_positions:
            map_title_to_past_member_positions[abstracted_title] = []
        map_title_to_past_member_positions[abstracted_title].append(past_member_position)
    
    # Setup title order
    titles_in_order = []
    for title in Position.get_sorted_abstracted_titles():
        if title in map_title_to_past_member_positions:
            titles_in_order.append(title)

    context = {
        'current_members': current_member_positions,
        'graduated_phd_students': list_of_graduated_phd_students,
        'past_members': past_member_positions,
        'debug': settings.DEBUG,
        'sorted_past_member_titles': titles_in_order,
        'map_title_to_past_members': map_title_to_past_member_positions,
        'navbar_white': True
    }

    # Render is a Django helper function. It combines a given template—in this case people.html—with
    # a context dictionary and returns an HttpResponse object with that rendered text.
    # See: https://docs.djangoproject.com/en/4.0/topics/http/shortcuts/#render
    render_func_start_time = time.perf_counter()
    render_response = render(request, 'website/people.html', context)
    render_func_end_time = time.perf_counter()
    _logger.debug(f"Took {render_func_end_time - render_func_start_time:0.4f} seconds to create render_response")

    func_end_time = time.perf_counter()
    _logger.debug(f"Rendered people in {func_end_time - func_start_time:0.4f} seconds")
    context['render_time'] = func_end_time - func_start_time

    return render_response