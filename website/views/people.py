from django.conf import settings # for access to settings variables, see https://docs.djangoproject.com/en/4.0/topics/settings/#using-settings-in-python-code
from website.models import Banner, Position, Person, Publication
import website.utils.ml_utils as ml_utils 
import operator
from django.shortcuts import render # for render https://docs.djangoproject.com/en/4.0/topics/http/shortcuts/#render

from django.db.models import Q # allow for complex queries, see: http://docs.djangoproject.com/en/4.2/topics/db/queries/#complex-lookups-with-q-objects

from datetime import date

# For logging
import time
import logging

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

def people(request):
    func_start_time = time.perf_counter()
    _logger.debug(f"Starting views/people at {func_start_time:0.4f}")

    # current_members = Person.objects.filter(position__is_current_member=True).distinct()
    # current_members = Position.objects.filter(start_date__lte=date.today(),
    #                                           end_date__isnull=True | end_date__gte=date.today())
    
    # In Django, keyword objects are AND'ed together. If we want more complex queries (e.g,. with OR statements),
    # we need to use Q objects. See: https://docs.djangoproject.com/en/4.2/topics/db/queries/#complex-lookups-with-q-objects
    # We want to get all current members ordered by start date (ascending)
    current_members = Position.objects.filter(Q(start_date__lte=date.today()), # start date is in the past
                            Q(end_date__isnull=True) | Q(end_date__gte=date.today()), # end date is in the future or null
                            Q(role=Position.MEMBER)).distinct('person__id', 'start_date').order_by('person__id', 'start_date') 

    # Get PHD students with dissertations
    dissertations = Publication.objects.filter(pub_venue_type=Publication.PHD_DISSERTATION).order_by('-date')
    list_of_graduated_phd_students = []
    for dissertation in dissertations:
        grad_student = dissertation.get_person()
        list_of_graduated_phd_students.append(grad_student)

    context = {
        'current_members': current_members,
        'graduated_phd_students': list_of_graduated_phd_students,
        'debug': settings.DEBUG
    }

    # People rendering
    func_end_time = time.perf_counter()
    _logger.debug(f"Rendered people in {func_end_time - func_start_time:0.4f} seconds")
    context['render_time'] = func_end_time - func_start_time

    # Render is a Django helper function. It combines a given template—in this case people.html—with
    # a context dictionary and returns an HttpResponse object with that rendered text.
    # See: https://docs.djangoproject.com/en/4.0/topics/http/shortcuts/#render
    return render(request, 'website/people.html', context)