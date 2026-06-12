from django.conf import settings
from website.models import Publication, Award, AwardType
from django.shortcuts import render

import time
import logging

_logger = logging.getLogger(__name__)


def awards(request):
    func_start_time = time.perf_counter()
    _logger.debug(f"Starting views/awards at {func_start_time:0.4f}")

    # People & project distinctions, grouped into ordered sections by award_type.
    # Section order follows the declaration order of AwardType; empty sections
    # are skipped so neither the page nor the sidebar shows a bare heading.
    # NOTE: awards with no award_type set (or a stale value not in AwardType) are
    # omitted -- assign a valid type in the admin to make them appear.
    all_distinctions = list(Award.objects.order_by('-date'))
    distinction_sections = []
    for value, label in AwardType.choices:
        section_awards = [a for a in all_distinctions if a.award_type == value]
        if section_awards:
            distinction_sections.append({'label': label, 'awards': section_awards})

    # Paper awards (from Publication.award). "Other" is defined as the negation
    # of is_best_paper(), so new award types fall through automatically.
    awarded_pubs = (Publication.objects
                    .exclude(award__isnull=True)
                    .exclude(award='')
                    .order_by('-date'))
    best_paper_pubs = [p for p in awarded_pubs if p.is_best_paper()]
    other_award_pubs = [p for p in awarded_pubs if not p.is_best_paper()]

    context = {
        'distinction_sections': distinction_sections,
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