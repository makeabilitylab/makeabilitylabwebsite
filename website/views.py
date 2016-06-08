import operator
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, render
from .models import Person, Publication, Talk, Position, Banner

def index(request):
    max_favorite_banners = 5
    max_banners = 5
    favorite_banners = Banner.objects.filter(page=Banner.FRONTPAGE, favorite=True)
    other_banners = Banner.objects.filter(page=Banner.FRONTPAGE, favorite=False)
    banners = []
    for banner in favorite_banners:
        if len(banners) > max_favorite_banners:
            break
        banners.append(banner)
    for banner in other_banners:
        if len(banners) > max_banners:
            break
        banners.append(banner)

    context = { 'people': Person.objects.all(), 'banners': banners }
    return render(request, 'website/index.html', context)

def people(request):

    # template = loader.get_template('website/people.html')
    # context = RequestContext(request, {
    #     'people': Person.objects.all(),
    # })
    # return HttpResponse(template.render(context))

    positions = Position.objects.all()
    active_members = []
    active_prof_grad = []
    active_prof = []
    active_postdoc = []
    active_phd = []
    active_ms = []
    active_undergrad = []
    active_highschool = []
    alumni_members = []
    cur_collaborators = []
    past_collaborators = []

    for position in positions:
        if position.is_active_member():
            if position.is_prof() or position.is_grad():
                if position.is_prof():
                    active_prof.append(position)
                elif position.title == Position.POST_DOC:
                    active_postdoc.append(position)
                elif position.title == Position.PHD_STUDENT:
                    active_phd.append(position)
                elif position.title == Position.MS_STUDENT:
                    active_ms.append(position)
            elif position.title == Position.UGRAD:
                active_undergrad.append(position)
            elif position.title == Position.HIGH_SCHOOL:
                active_highschool.append(position)
        elif position.is_alumni_member():
            alumni_members.append(position)
        elif position.is_collaborator():
            if position.is_active_collaborator():
                cur_collaborators.append(position)
            else:
                past_collaborators.append(position)
    
    # sort active members/collaborators by seniority, and alumni/past 
    # collaborators by end data (most recent first)
    active_prof.sort(key=operator.attrgetter('start_date'))
    active_postdoc.sort(key=operator.attrgetter('start_date'))
    active_phd.sort(key=operator.attrgetter('start_date'))
    active_ms.sort(key=operator.attrgetter('start_date'))
    active_undergrad.sort(key=operator.attrgetter('start_date'))
    active_highschool.sort(key=operator.attrgetter('start_date'))
    alumni_members.sort(key=operator.attrgetter('end_date'))
    alumni_members.reverse()
    cur_collaborators.sort(key=operator.attrgetter('start_date'))
    past_collaborators.sort(key=operator.attrgetter('end_date'))
    past_collaborators.reverse()

    # merge lists for easier display
    active_prof_grad.extend(active_prof)
    active_prof_grad.extend(active_postdoc)
    active_prof_grad.extend(active_phd)
    active_prof_grad.extend(active_ms)

    max_favorite_banners = 5
    max_banners = 5
    favorite_banners = Banner.objects.filter(page=Banner.PEOPLE, favorite=True)
    other_banners = Banner.objects.filter(page=Banner.PEOPLE, favorite=False)
    banners = []
    for banner in favorite_banners:
        if len(banners) > max_favorite_banners:
            break;
        banners.append(banner)
    for banner in other_banners:
        if len(banners) > max_banners:
            break;
        banners.append(banner)

    context = {
        'people' : Person.objects.all(),
        'active_members' : active_members,
        'active_prof_grad' : active_prof_grad,
        'active_prof' : active_prof,
        'active_postdoc' : active_postdoc,
        'active_phd' : active_phd,
        'active_ms' : active_ms,
        'active_undergrad' : active_undergrad,
        'active_highschool' : active_highschool,
        'alumni_members' : alumni_members,
        'cur_collaborators' : cur_collaborators,
        'past_collaborators' : past_collaborators,
        'positions' : positions,
        'banners' : banners

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
    max_favorite_banners = 5
    max_banners = 5
    favorite_banners = Banner.objects.filter(page=Banner.PUBLICATIONS, favorite=True)
    other_banners = Banner.objects.filter(page=Banner.PUBLICATIONS, favorite=False)
    banners = []
    for banner in favorite_banners:
        if len(banners) > max_favorite_banners:
            break;
        banners.append(banner)
    for banner in other_banners:
        if len(banners) > max_banners:
            break;
        banners.append(banner)
    context = { 'publications': Publication.objects.all(), 'banners': banners }
    return render(request, 'website/publications.html', context)

def talks(request):
    max_favorite_banners = 5
    max_banners = 5
    favorite_banners = Banner.objects.filter(page=Banner.TALKS, favorite=True)
    other_banners = Banner.objects.filter(page=Banner.TALKS, favorite=False)
    banners = []
    for banner in favorite_banners:
        if len(banners) > max_favorite_banners:
            break;
        banners.append(banner)
    for banner in other_banners:
        if len(banners) > max_banners:
            break;
        banners.append(banner)
    context = { 'talks': Talk.objects.all(), 'banners': banners }
    return render(request, 'website/talks.html', context)
