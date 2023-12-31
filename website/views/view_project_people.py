from django.shortcuts import render
from website.models import Project, Person
from django.http import Http404
from django.db.models import Q

def view_project_people(request):
    project_name = request.GET.get('project_name', None)
    if project_name:
        project = Project.objects.get(Q(name=project_name) | Q(short_name=project_name))
        # members = Member.objects.filter(project=project).order_by('-time_worked')
        people = project.get_people()

        context = {'project': project,
                   'people': people}
        
        return render(request, 'website/view_project_people.html', context)
    else:
        raise Http404('Project not found.')