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

    projects = person.get_projects
    project_count = len(projects)
    publication_count = person.publication_set.count()

    # start_date = person.projectrole_set.order_by('start_date').first().start_date
    # years_in_lab = (datetime.date.today() - start_date).days // 365
    total_time_in_lab = person.get_total_time_in_lab()
    #total_time_in_role = person.get_total_time_in_current_position()
    humanized_duration = None
    if total_time_in_lab:
        humanized_duration = humanize_duration(total_time_in_lab)

    print(f"total_time_in_lab={total_time_in_lab}, humanized_duration={humanized_duration}")
    
    bio = f"{person.get_full_name()}"
    if not person.has_started:
        latest_position = person.get_latest_position
        if latest_position and latest_position.start_date:
            bio += f" will be joining the Makeability Lab on {latest_position.start_date}."
        else:
            bio += " will be joining the Makeability Lab."   
    elif person.is_current_member:
        bio += f" is currently a {person.get_current_title} in the Makeability Lab."
    elif person.is_current_collaborator:
        bio += f" is currently a collaborator with the Makeability Lab."
    elif person.is_alumni_member:
        bio += f" was a {person.get_current_title} in the Makeability Lab"
    elif person.is_past_collaborator:
        bio += f" was a collaborator with the Makeability Lab"
    
    
    if person.is_current_member:
        bio += f" {person.first_name} has been in the lab for {humanized_duration}"
    elif person.is_current_collaborator:
        bio += f" {person.first_name} has collaborated with the lab for {humanized_duration}"
    elif person.is_alumni_member or person.is_past_collaborator:
        bio += f" for {humanized_duration}"
        start_date_str = person.get_start_date.strftime("%b %Y")
        end_date_str = person.get_end_date.strftime("%b %Y") if person.get_end_date else "present"
            
        bio += f" ({start_date_str} to {end_date_str})."
        bio += f" {person.first_name} "
   
    if ((person.is_current_member or person.is_current_collaborator) and
        (project_count > 0 or publication_count > 0)): 
        bio += " and"
    elif not person.is_alumni_member and not person.is_past_collaborator:
        bio += "."

    if project_count > 0 or publication_count > 0:
        bio += " contributed to"

    if project_count == 1:
        proj = person.projectrole_set.first().project;
        bio += f" a project called <a href='/project/{proj.short_name}'>{proj.name}</a>"
    elif project_count > 1: 
        bio += f" {project_count} projects, including"
        
        for index, proj in enumerate(projects, start=1):
            bio += f" <a href='/project/{proj.short_name}'>{proj.name}</a>"
            if project_count == 2 and index == 1:
                bio += " and"
            elif index < project_count and index != project_count - 1:
                bio += ","
            elif index < project_count:
                bio += ", and"
            else:
                bio += "."
            
            if index == 3:
                break
    
    if publication_count > 0:
        if publication_count == 1:
            bio += f" as well as {publication_count} publication."
        else:
            bio += f" as well as {publication_count} publications."
    elif project_count > 1:
        bio += "."

    # Add mentorship information
    grad_mentors = person.get_grad_mentors()
    mentor_count = grad_mentors.count()
    _logger.debug(f"{person.first_name} has grad_mentors={grad_mentors}, mentor_count={mentor_count}")
    if grad_mentors.exists():

        bio += f" {person.first_name}"

        if person.is_active:
            bio += " is mentored by"
        else:
            bio += " was mentored by"

        for index, mentor in enumerate(grad_mentors):
            bio += f" <a href='/member/{mentor.get_url_name()}'>{mentor.get_full_name()}</a>"
            if mentor_count == 2 and index == 0:
                bio += " and"
            elif index < mentor_count - 1:
                bio += ","
            elif index >= mentor_count - 1:
                bio += ", and"
            
        bio += "." 

    # Add mentee information; get a random set
    mentees = person.get_mentees(randomize=True)
    mentee_count = mentees.count()
    max_mentees_to_display = min(3, mentees.count())
    _logger.debug(f"""{person.first_name} has mentees={mentees}, mentee_count={mentee_count}, 
                  max_mentees_to_display={max_mentees_to_display}""")
    if mentees.exists():
        bio += f" During their time in the lab, {person.first_name} mentored"

        if mentee_count == 1:
            bio += " 1 Makeability Lab student,"
            bio += f" <a href='/member/{mentees.first().get_url_name()}'>{mentees.first().get_full_name()}</a>."
        else:

            if mentees.count() <= 3:
                bio += f" {mentee_count} Makeability Lab students:"
            else:
                bio += f" {mentee_count} Makeability Lab students, including"

            for index, mentee in enumerate(mentees):
                bio += f" <a href='/member/{mentee.get_url_name()}'>{mentee.get_full_name()}</a>"
                if max_mentees_to_display == 2 and index == 0:
                    bio += " and"
                elif index < max_mentees_to_display - 1:
                    bio += ","
                
                if mentee_count > 2 and index == max_mentees_to_display - 2:
                    bio += " and"

                if index >= max_mentees_to_display - 1:
                    break

            bio += "."

    return bio

def humanize_duration(duration):
    """Given a timedelta object, returns a humanized string of the duration (e.g., 1.5 years)"""
    total_months = duration.total_seconds() / (30 * 24 * 60 * 60)

    # Calculate years and months
    years = total_months // 12
    months = total_months % 12

    if years >= 1:
        return f"{years + months/12:.1f} years"
    else:
        return f"{months:.1f} months"