from django.conf import settings # for access to settings variables, see https://docs.djangoproject.com/en/4.0/topics/settings/#using-settings-in-python-code
from website.models import Banner, Person, News, Talk, Video, Publication
import website.utils.ml_utils as ml_utils 
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.core.exceptions import MultipleObjectsReturned

# For logging
import time
import logging
from django.http import Http404

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

def member(request, member_name=None, member_id=None):
    func_start_time = time.perf_counter()
    _logger.debug(f"Starting views/member member_id={member_id} and member_name={member_name} at {func_start_time:0.4f}")

    # person = None
    # This code block gets a person object either from the member id or the url_name.
    # If the member_id is a digit, it's assumed to be the primary key (pk) of the Person object
    # The get_object_or_404 function is then used to retrieve the Person object with this pk. 
    # If no such Person object exists, the function will raise a 404 error.
    # If the member_id is not a digit, it's assumed to be the url-friendly name (url_name).
    # if (member_id.isdigit()):
    #     person = get_object_or_404(Person, pk=member_id)
    # else:
    #     person = get_object_or_404(Person, url_name__iexact=member_id)

    person = None
    if member_id is not None:
        _logger.debug(f"Found a member_id={member_id}, checking for a person with that id")
        person = get_object_or_404(Person, id=member_id)
    elif member_name is not None:
        _logger.debug(f"Found a member_name={member_name}, checking for a url_name match")
        try:
            # Try a case-insensitive exact match
            person = get_object_or_404(Person, url_name__iexact=member_name)
        except MultipleObjectsReturned:
            # This should not happen if url_name uniqueness is working correctly
            # Log error and return the most recently modified person as fallback
            _logger.error(f"Multiple people found with url_name={member_name}! This indicates url_name uniqueness is broken. Returning most recent.")
            person = Person.objects.filter(url_name__iexact=member_name).order_by('-modified_date').first()
            if person is None:
                raise Http404("No person matches the given query.")
        except Http404:
            _logger.debug(f"{member_name} not found for url_name, looking for closest match in database")
            closest_urlname = get_closest_urlname_in_database(member_name)
            person = get_object_or_404(Person, url_name__iexact=closest_urlname)

            # Redirect to the correct URL for the closest match
            return redirect('website:member_by_name', member_name=person.url_name)
    else:
        raise Http404("No person matches the given query.")

    news_items_num = 5  # Defines the number of news items that will be selected
    # all_banners = Banner.objects.filter(page=Banner.PEOPLE)
    # displayed_banners = ml_utils.choose_banners(all_banners)

    

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
    """Auto-generates a bio using list construction to prevent grammar errors."""
    
    # 1. Generate the Role Sentence
    role_parts = [person.get_full_name()]
    
    # Calculate duration safely
    total_time = person.get_total_time_in_lab()
    duration_str = humanize_duration(total_time) if total_time else ""

    if not person.has_started:
        date_str = f" on {person.get_latest_position.start_date}" if person.get_latest_position and person.get_latest_position.start_date else ""
        role_parts.append(f"will be joining the Makeability Lab{date_str}.")
    elif person.is_current_member:
        role_parts.append(f"is currently a {person.get_current_title} in the Makeability Lab.")
        if duration_str:
            role_parts.append(f"{person.first_name} has been in the lab for {duration_str}.")
    elif person.is_alumni_member:
        role_parts.append(f"was a {person.get_current_title} in the Makeability Lab")
        if duration_str:
            role_parts.append(f"for {duration_str}")
        
        start = person.get_start_date.strftime("%b %Y")
        end = person.get_end_date.strftime("%b %Y") if person.get_end_date else "present"
        role_parts.append(f"({start} to {end}).")

    # Combine the introductory sentences
    bio_sentences = [" ".join(role_parts).replace(" .", ".")]

    # 2. Generate the Contributions Sentence
    # FIX: Ensure projects is a list and sorted
    projects = list(person.get_projects)
    projects.sort(key=lambda x: x.name) 
    
    proj_count = len(projects)
    pub_count = person.publication_set.count()

    if proj_count > 0 or pub_count > 0:
        contrib_str = f"{person.first_name} contributed to"
        
        # --- Build Project String ---
        if proj_count > 0:
            if proj_count == 1:
                proj = projects[0]
                contrib_str += f" a project called <a href='/project/{proj.short_name}'>{proj.name}</a>"
            else:
                shown_projects = projects[:3]
                proj_links = [f"<a href='/project/{p.short_name}'>{p.name}</a>" for p in shown_projects]
                
                # FIX: Standard English list formatting
                if len(proj_links) == 2:
                    # Case: "Project A and Project B"
                    list_str = " and ".join(proj_links)
                else:
                    # Case: "Project A, Project B, and Project C"
                    proj_links[-1] = "and " + proj_links[-1]
                    list_str = ", ".join(proj_links)

                if proj_count <= 3:
                     contrib_str += f" {proj_count} projects: {list_str}"
                else:
                     contrib_str += f" {proj_count} projects, including {list_str}"

        # --- Build Publication String ---
        if pub_count > 0:
            # We add a comma before "as well as" if there was a project list preceding it
            connector = ", as well as" if proj_count > 0 else ""
            plural = "s" if pub_count > 1 else ""
            contrib_str += f"{connector} {pub_count} publication{plural}"
        
        bio_sentences.append(contrib_str + ".")

    # 3. Generate Mentor Sentence
    grad_mentors = list(person.get_grad_mentors()) # Convert to list for easy indexing
    if grad_mentors:
        verb = "is" if person.is_active else "was"
        mentor_links = [f"<a href='/member/{m.get_url_name()}'>{m.get_full_name()}</a>" for m in grad_mentors]
        
        if len(mentor_links) > 1:
            mentor_links[-1] = "and " + mentor_links[-1]
        
        mentor_str = ", ".join(mentor_links) if len(mentor_links) > 2 else " ".join(mentor_links)
        bio_sentences.append(f"{person.first_name} {verb} mentored by {mentor_str}.")

    # 4. Generate Mentee Sentence (Logic simplified)
    mentees = person.get_mentees(randomize=True)
    mentee_count = mentees.count()
    if mentee_count > 0:
        display_limit = 3
        shown_mentees = [m for m in mentees[:display_limit]] # Force evaluation
        mentee_links = [f"<a href='/member/{m.get_url_name()}'>{m.get_full_name()}</a>" for m in shown_mentees]
        
        intro = f"During their time in the lab, {person.first_name} mentored"
        
        if mentee_count == 1:
             bio_sentences.append(f"{intro} 1 Makeability Lab student, {mentee_links[0]}.")
        else:
            sep = ":" if mentee_count <= display_limit else ", including"
            
            if len(mentee_links) > 1:
                mentee_links[-1] = "and " + mentee_links[-1]
            
            list_str = ", ".join(mentee_links) if len(mentee_links) > 2 else " ".join(mentee_links)
            bio_sentences.append(f"{intro} {mentee_count} Makeability Lab students{sep} {list_str}.")

    return " ".join(bio_sentences)

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
    
def get_closest_urlname_in_database(query_urlname, cutoff=0.8):
    """
    Retrieves the closest matching url_name from the database based on the provided query url_name.
    Args:
        query_urlname (str): The url_name to search for in the database.
        cutoff (float, optional): The similarity threshold for matching url_names. Defaults to 0.8.
    Returns:
        str: The closest matching url_name from the database.
    """
    
    all_urlnames = Person.objects.values_list('url_name', flat=True)
    return ml_utils.get_closest_match(query_urlname, all_urlnames, cutoff)