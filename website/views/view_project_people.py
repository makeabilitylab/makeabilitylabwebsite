from django.shortcuts import render
from website.models import Project, Person
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.db.models import Q

def view_project_people(request):
    """This page is intended to be used internally in our lab to view the people 
       associated with a project. It should be useful for generating screenshots
       for our talks, etc.
    """
    project_name = request.GET.get('project_name', None)
    split_char = ','
    if project_name:
        if split_char in project_name:  # check for the existence of a comma
            project_names = project_name.split(split_char)  # split the string into a list of project names
        else:
            project_names = [project_name]  # if there's no comma, create a list with a single project name

        people_dict = {}  # create an empty dictionary
        for project_name in project_names:
            project = get_object_or_404(Project, Q(name=project_name) | Q(short_name=project_name))
            people = project.get_people()
            for person in people:
                if person not in people_dict:
                    people_dict[person] = person.get_total_time_on_project(project)
                else:
                    people_dict[person] += person.get_total_time_on_project(project)

        # Sort the people by total time worked on the projects
        # people_sorted is a list of tuples, where each tuple contains a person and their 
        # total time worked on the projects, sorted in descending order (because reverse=True is used).
        people_sorted = sorted(people_dict.items(), key=lambda item: item[1], reverse=True)

        # List of people sorted by time
        people_only = [person[0] for person in people_sorted]

        context = {'projects': project_names,
                   'people_sorted': people_sorted,
                   'people_only': people_only}
        
        return render(request, 'website/view_project_people.html', context)
    else:
        raise Http404('project_name needs to be specified not found.')