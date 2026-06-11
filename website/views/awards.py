from django.conf import settings
from website.models import Publication, PersonAward
from django.shortcuts import render

import time
import logging

_logger = logging.getLogger(__name__)


def awards(request):
    func_start_time = time.perf_counter()
    _logger.debug(f"Starting views/awards at {func_start_time:0.4f}")

    # People awards & distinctions (fellowships, faculty honors, society
    # recognitions). Flat, newest-first -- no year grouping, so gap years
    # aren't visually obvious.
    person_awards = PersonAward.objects.order_by('-date')

    # Paper awards. We pull every awarded pub, then split in Python so that
    # "Other" is the *negation* of is_best_paper() -- new award types (e.g.,
    # Belonging & Inclusion, Diversity & Inclusion) land in "Other"
    # automatically without needing to edit this view.
    awarded_pubs = (Publication.objects
                    .exclude(award__isnull=True)
                    .exclude(award='')
                    .order_by('-date'))
    best_paper_pubs = [p for p in awarded_pubs if p.is_best_paper()]
    other_award_pubs = [p for p in awarded_pubs if not p.is_best_paper()]

    context = {
        'person_awards': person_awards,
        'best_paper_pubs': best_paper_pubs,
        'other_award_pubs': other_award_pubs,
        'debug': settings.DEBUG,
        'navbar_white': True,
    }

    render_response = render(request, 'website/awards.html', context)

    func_end_time = time.perf_counter()
    _logger.debug(f"Prepared awards page in {func_end_time - func_start_time:0.4f} seconds")
    context['render_time'] = func_end_time - func_start_time

    return render_response
