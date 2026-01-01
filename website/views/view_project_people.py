"""
View for displaying project people with customizable sidebar controls.

This internal page allows lab members to view people associated with projects
with options for filtering, sorting, grouping, and display customization.
Useful for generating screenshots for talks, papers, and presentations.

URL Parameters (for state persistence):
    - projects: Comma-separated list of project short_names
    - sort: Sort order (time_on_project, start_date, seniority)
    - group: Grouping (none, position)
    - show_title: Whether to show titles (1 or 0)
    - show_dates: Whether to show date range (1 or 0)
    - show_school: Whether to show school (1 or 0)
    - full_school: Whether to show full school name vs abbreviated (1 or 0)
    - show_pub: Whether to highlight people who published on selected projects (1 or 0)
"""

from django.shortcuts import render
from django.http import JsonResponse
from website.models import Project, Person
from website.models.position import Position, Title
from datetime import date
import json

# For generating thumbnail URLs server-side (using easy-thumbnails)
from easy_thumbnails.files import get_thumbnailer


def view_project_people(request):
    """
    Renders the project people page with sidebar controls.
    
    This page displays people associated with selected projects and provides
    a collapsible sidebar for customizing the display. All filtering, sorting,
    and grouping is done client-side for instant updates.
    
    Args:
        request: Django HTTP request object
        
    Returns:
        Rendered HTML template with context containing all projects and people data
    """
    # Fetch all projects for the sidebar, ordered by name
    all_projects = Project.objects.all().order_by('name')
    
    # Build project data for the sidebar
    projects_data = []
    for project in all_projects:
        projects_data.append({
            'id': project.id,
            'name': project.name,
            'short_name': project.short_name,
            'is_active': not project.has_ended() if hasattr(project, 'has_ended') else True,
            'people_count': project.get_people_count(),
        })
    
    # Get all people who have ever worked on any project
    # We'll filter client-side based on selected projects
    all_people_on_projects = Person.objects.filter(
        projectrole__isnull=False
    ).distinct().select_related().prefetch_related(
        'position_set',
        'projectrole_set',
        'projectrole_set__project',
        'publication_set',
        'publication_set__projects'
    )
    
    # Build comprehensive people data for client-side operations
    people_data = []
    for person in all_people_on_projects:
        latest_position = person.get_latest_position
        earliest_position = person.get_earliest_position
        
        # Get abstracted title for grouping
        abstracted_title = None
        title_order = 999
        if latest_position:
            abstracted_title = Position.get_abstracted_title(latest_position)
            title_order = latest_position.get_title_index()
        
        # Build project roles data for this person
        # We store dates as date objects during iteration, then convert to ISO strings at the end
        project_roles_raw = {}
        for role in person.projectrole_set.all():
            proj_short_name = role.project.short_name
            if proj_short_name not in project_roles_raw:
                project_roles_raw[proj_short_name] = {
                    'total_days': 0,
                    'start_date': None,
                    'end_date': None,
                }
            
            # Calculate days on project for this role
            end = role.end_date or date.today()
            start = role.start_date
            days = (end - start).days
            project_roles_raw[proj_short_name]['total_days'] += days
            
            # Track earliest start and latest end (comparing date objects)
            if project_roles_raw[proj_short_name]['start_date'] is None or start < project_roles_raw[proj_short_name]['start_date']:
                project_roles_raw[proj_short_name]['start_date'] = start
            if project_roles_raw[proj_short_name]['end_date'] is None or end > project_roles_raw[proj_short_name]['end_date']:
                project_roles_raw[proj_short_name]['end_date'] = end
        
        # Convert dates to ISO strings for JSON serialization
        project_roles = {}
        for proj_short_name, role_data in project_roles_raw.items():
            project_roles[proj_short_name] = {
                'total_days': role_data['total_days'],
                'start_date': role_data['start_date'].isoformat() if role_data['start_date'] else None,
                'end_date': role_data['end_date'].isoformat() if role_data['end_date'] else None,
            }
        
        # Build set of projects this person has published on
        # This is used for the "highlight published" indicator feature
        projects_published_on = set()
        for pub in person.publication_set.all():
            for proj in pub.projects.all():
                projects_published_on.add(proj.short_name)
        
        # Generate thumbnail URL for this person's image
        # Uses easy-thumbnails with django-image-cropping
        image_url = ''
        if person.image:
            try:
                thumbnailer = get_thumbnailer(person.image)
                thumbnail_options = {
                    'size': (245, 245),  # PERSON_THUMBNAIL_SIZE from person.py
                    'crop': True,
                    'upscale': True,
                    'detail': True,
                }
                # Add cropping box if available (from django-image-cropping)
                if person.cropping:
                    thumbnail_options['box'] = person.cropping
                
                thumb = thumbnailer.get_thumbnail(thumbnail_options)
                image_url = thumb.url if thumb else ''
            except Exception:
                # Fallback to original image URL if thumbnail generation fails
                image_url = person.image.url if person.image else ''
        
        # Build person data object
        person_obj = {
            'id': person.id,
            'first_name': person.first_name,
            'last_name': person.last_name,
            'full_name': person.get_full_name(),
            'url_name': person.url_name,
            
            # Image URL (pre-computed thumbnail)
            'image_url': image_url,
            
            # Position info
            'title': latest_position.title if latest_position else 'Unknown',
            'abstracted_title': abstracted_title or 'Unknown',
            'title_order': title_order,
            
            # School/department info
            'school': latest_position.school if latest_position else '',
            'school_abbreviated': latest_position.get_school_abbreviated() if latest_position else '',
            'department': latest_position.department if latest_position else '',
            'department_abbreviated': latest_position.get_department_abbreviated() if latest_position else '',
            
            # Date info
            'lab_start_date': earliest_position.start_date.isoformat() if earliest_position else None,
            'lab_end_date': latest_position.end_date.isoformat() if latest_position and latest_position.end_date else None,
            'date_range_str': latest_position.get_date_range_as_str() if latest_position else '',
            
            # Seniority (lower = more senior based on TITLE_ORDER_MAPPING)
            'seniority_index': title_order,
            
            # Project-specific data
            'project_roles': project_roles,
            
            # Projects this person has published on (for highlight indicator)
            'projects_published_on': list(projects_published_on),
            
            # Special case for lab director
            'is_director': person.last_name == 'Froehlich',
        }
        
        people_data.append(person_obj)
    
    # Get sorted abstracted titles for grouping
    abstracted_titles = list(Position.get_sorted_abstracted_titles())
    # Convert Title enum values to their string representations
    abstracted_titles_clean = []
    for t in abstracted_titles:
        if hasattr(t, 'value'):
            abstracted_titles_clean.append(t.value)
        else:
            abstracted_titles_clean.append(str(t))
    
    context = {
        'projects_json': json.dumps(projects_data),
        'people_json': json.dumps(people_data),
        'abstracted_titles_json': json.dumps(abstracted_titles_clean),
    }
    
    return render(request, 'website/view_project_people.html', context)