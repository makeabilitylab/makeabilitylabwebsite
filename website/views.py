from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, render
from .models import Person, Publication, Talk, Position

def index(request):
    context = { 'people': Person.objects.all() }
    return render(request, 'website/index.html', context)

def people(request):

    # template = loader.get_template('website/people.html')
    # context = RequestContext(request, {
    #     'people': Person.objects.all(),
    # })
    # return HttpResponse(template.render(context))

    positions = Position.objects.all()
    active_members = []
    alumni_members = []
    cur_collaborators = []
    past_collaborators = []

    for position in positions:
        if position.is_active_member():
            active_members.append(position)
        elif position.is_alumni_member():
            alumni_members.append(position)
        elif position.is_collaborator():
            cur_collaborators.append(position)

    context = {
        'people' : Person.objects.all(),
        'active_members' : active_members,
        'alumni_members' : alumni_members,
        'cur_collaborators' : cur_collaborators,
        'positions' : positions
    }
    return render(request, 'website/people.html', context)


def member(request, member_id):
    # try:
    #     person = Person.objects.get(pk=member_id)
    # except Person.DoesNotExist:
    #     raise Http404("Person does not exist")
    # return render(request, 'website/member.html', {'person': person})
    person = get_object_or_404(Person, pk=member_id)
    return render(request, 'website/member.html', {'person': person})

def publications(request):
    context = { 'publications': Publication.objects.all() }
    return render(request, 'website/publications.html', context)

def talks(request):
    context = { 'talks': Talk.objects.all() }
    return render(request, 'website/talks.html', context)
