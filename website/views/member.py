from django.conf import settings # for access to settings variables, see https://docs.djangoproject.com/en/4.0/topics/settings/#using-settings-in-python-code
from website.models import Banner, Person, News, Talk, Video, Publication
import website.utils.ml_utils as ml_utils 
from django.shortcuts import render, get_object_or_404
from django.db.models import Q

# For logging
import time
import logging

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

def member(request, member_id):
    func_start_time = time.perf_counter()
    _logger.debug(f"Starting views/member member_id={member_id} at {func_start_time:0.4f}")

    news_items_num = 5  # Defines the number of news items that will be selected
    # all_banners = Banner.objects.filter(page=Banner.PEOPLE)
    # displayed_banners = ml_utils.choose_banners(all_banners)

    # This code block gets a person object either from the member id or the url_name.
    # If the member_id is a digit, it's assumed to be the primary key (pk) of the Person object
    # The get_object_or_404 function is then used to retrieve the Person object with this pk. 
    # If no such Person object exists, the function will raise a 404 error.
    # If the member_id is not a digit, it's assumed to be the url-friendly name (url_name).
    if (member_id.isdigit()):
        person = get_object_or_404(Person, pk=member_id)
    else:
        person = get_object_or_404(Person, url_name__iexact=member_id)

    # Returns QuerySet of News objects that mention the specified person. 
    # The order_by('-date') part sorts the QuerySet by date in descending order 
    # (so the most recent news comes first), and [:4] limits the QuerySet to 
    # the first 4 objects.
    news = News.objects.filter(people=person).order_by('-date')[:4]
    latest_position = person.get_latest_position
    publications = person.publication_set.order_by('-date')
    talks = person.talk_set.order_by('-date')
    videos = get_videos_by_author(person)
    project_roles = person.projectrole_set.order_by('start_date')
    projects = person.get_projects

    left_align_headers = (len(projects) <= 4 and len(publications) <= 3 and 
                          len(talks) <= 3 and len(videos) <= 3)
    
    auto_generated_bio = ""
    if not person.bio:
        auto_generated_bio = auto_generate_bio(person)

    # filter projects to those that have a thumbnail and have been published
    # TODO: might consider moving this to ml_utils so we have consistent determination
    # of what projects to show publicly
    filtered_projects = list()
    for proj in projects:
        if proj.gallery_image is not None and proj.has_publication():
            filtered_projects.append(proj)
    projects = filtered_projects

    context = {'person': person,
               'auto_generated_bio': auto_generated_bio,
               'news': news,
               'talks': talks,
               'videos': videos,
               'publications': publications,
               'project_roles': project_roles,
               'projects' : projects,
               'position' : latest_position,
               # 'banners': displayed_banners,
               'left_align_headers': left_align_headers,
               'debug': settings.DEBUG,
               'navbar_white': True,
               'page_title': person.get_full_name()}
    
    

    # Render is a Django shortcut (aka helper function). It combines a given template—in this case
    # member.html—with a context dictionary and returns an HttpResponse object with that rendered text.
    # See: https://docs.djangoproject.com/en/4.0/topics/http/shortcuts/#render
    render_func_start_time = time.perf_counter()
    render_response = render(request, 'website/member.html', context)
    render_func_end_time = time.perf_counter()
    _logger.debug(f"Took {render_func_end_time - render_func_start_time:0.4f} seconds to create render_response")

    func_end_time = time.perf_counter()
    _logger.debug(f"Prepared person={person} in {func_end_time - func_start_time:0.4f} seconds")
    context['render_time'] = func_end_time - func_start_time

    return render_response

def get_videos_by_author(person):
    """Returns a queryset of videos that the given person is an author on"""
    # Get all Publications where the given person is an author
    publication_videos = Publication.objects.filter(authors=person).values_list('video', flat=True)

    # Get all Talks where the given person is an author
    talk_videos = Talk.objects.filter(authors=person).values_list('video', flat=True)

    # Combine the two querysets and order by date
    videos = Video.objects.filter(Q(id__in=publication_videos) | 
                                  Q(id__in=talk_videos)).order_by('-date')

    return videos

def auto_generate_bio(person):
    """Auto-generates a bio for the given person based on their contributions to the lab"""
    project_count = person.projectrole_set.count()
    publication_count = person.publication_set.count()
    # start_date = person.projectrole_set.order_by('start_date').first().start_date
    # years_in_lab = (datetime.date.today() - start_date).days // 365
    total_time_in_lab = person.get_total_time_in_lab()
    #total_time_in_role = person.get_total_time_in_current_position()
    humanized_duration = humanize_duration(total_time_in_lab)
    
    bio = f"{person.first_name} "
    if person.is_current_member:
        bio += f"is a current {person.get_current_title} in the Makeability Lab."
    elif person.is_current_collaborator:
        bio += f"is a current collaborator with the Makeability Lab."
    elif person.is_alumni_member:
        bio += f"was a {person.get_current_title} in the Makeability Lab "
    elif person.is_past_collaborator:
        bio += f"was a collaborator with the Makeability Lab "

    if person.is_current_member or person.is_current_collaborator:
        bio += f" They have been in the lab for {humanized_duration} and have contributed to"
    elif person.is_alumni_member or person.is_past_collaborator:
        start_date_str = person.get_start_date.strftime("%b %Y")
        end_date_str = person.get_end_date.strftime("%b %Y") if person.get_end_date else "present"
            
        bio += f" from {start_date_str} to {end_date_str} and contributed to"
   
    project_word = "project" if project_count == 1 else "projects"
    publication_word = "publication" if publication_count == 1 else "publications"

    bio += f" {project_count} {project_word}"
    
    if publication_count > 0:
        bio += f" and {publication_count} {publication_word}."
    else:
        bio += "."

    return bio

def humanize_duration(duration):
    total_months = duration.total_seconds() / (30 * 24 * 60 * 60)
    years = total_months // 12
    months = total_months % 12

    if years >= 1:
        return f"{years + months/12:.1f} years"
    else:
        return f"{months} months"