import operator, datetime, random
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, render
from .models import Person, Publication, Talk, Position, Banner, News, Keyword, Video, Project, Project_umbrella
from django.conf import settings
from datetime import date

max_banners = 7

def weighted_choice(choices):
   total = sum(w for c, w in choices)
   r = random.uniform(0, total)
   upto = 0
   for c, w in choices:
      if upto + w >= r:
         return c
      upto += w
   # assert False, "Shouldn't get here"
   return choices[0][0]

def choose_banners(banners):
    banner_weights = []
    total_weight = 0
    for banner in banners:
        elapsed = (datetime.datetime.now().date() - banner.date_added).days / 31.0
        if elapsed <= 0:
            elapsed = 1.0 / 31.0
        weight = (100 if banner.favorite==True else 1) + 1.0 / elapsed
        banner_weights.append((banner, weight))
        total_weight += weight
    for i in range(0, len(banner_weights)):
        banner_weights[i] = (banner_weights[i][0], banner_weights[i][1] / total_weight)
        print(banner_weights[i][1])

    selected_banners = []
    for i in range(0, max_banners):
        if len(selected_banners) == len(banners):
            break
        banner = weighted_choice(banner_weights)
        selected_banners.append(banner)
        index = [y[0] for y in banner_weights].index(banner)
        total_weight -= banner_weights[index][1]
        del banner_weights[index]
        if len(banner_weights) == 0:
            break
        for i in range(0, len(banner_weights)):
            banner_weights[i] = (banner_weights[i][0], banner_weights[i][1] / total_weight)

    return selected_banners

#Every view is passed settings.DEBUG. This is used to insert the appropriate google analytics tracking when in production, and to not include it for development
 
def index(request):
    news_items_num = 5 # Defines the number of news items that will be selected
    papers_num = 3 # Defines the number of papers which will be selected
    talks_num = 8 # Defines the number of talks which will be selected
    videos_num = 2 # Defines the number of videos which will be selected
    all_banners = Banner.objects.filter(page=Banner.FRONTPAGE)
    displayed_banners = choose_banners(all_banners)
    print(settings.DEBUG)
    #Select recent news, papers, and talks.
    news_items = News.objects.order_by('-date')[:news_items_num]
    publications = Publication.objects.order_by('-date')[:papers_num]
    talks = Talk.objects.order_by('-date')[:talks_num]
    videos = Video.objects.order_by('-date')[:videos_num]
    context = { 'people': Person.objects.all(), 'banners': displayed_banners, 'news': news_items, 'publications': publications, 'talks': talks, 'videos':videos, 'debug': settings.DEBUG }
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

    all_banners = Banner.objects.filter(page=Banner.PEOPLE)
    displayed_banners = choose_banners(all_banners)

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
        'banners' : displayed_banners,
       'debug': settings.DEBUG

    }
    return render(request, 'website/people.html', context)


def member(request, member_id):
   # try:
   #     person = Person.objects.get(pk=member_id)
   # except Person.DoesNotExist:
   #     raise Http404("Person does not exist")
   # return render(request, 'website/member.html', {'person': person})
   news_items_num = 5 # Defines the number of news items that will be selected
   all_banners = Banner.objects.filter(page=Banner.PEOPLE)
   displayed_banners = choose_banners(all_banners)
   person = get_object_or_404(Person, pk=member_id)
   news = person.news_set.order_by('-date')[:news_items_num]
   publications = person.publication_set.order_by('-date')
   talks = person.talk_set.order_by('-date')
   return render(request, 'website/member.html', {'person': person, 'news': news, 'talks': talks, 'publications': publications, 'banners': displayed_banners, 'debug': settings.DEBUG})

def publications(request, filter=None):
    all_banners = Banner.objects.filter(page=Banner.PUBLICATIONS)
    displayed_banners = choose_banners(all_banners)
    context = { 'publications': Publication.objects.filter(date__range=["2012-01-01", date.today()]), 'banners': displayed_banners, 'filter': filter, 'debug': settings.DEBUG }
    return render(request, 'website/publications.html', context)

def talks(request, filter=None):
    all_banners = Banner.objects.filter(page=Banner.TALKS)
    displayed_banners = choose_banners(all_banners)
    context = { 'talks': Talk.objects.filter(date__range=["2012-01-01", date.today()]), 'banners': displayed_banners, 'filter': filter, 'debug': settings.DEBUG }
    return render(request, 'website/talks.html', context)

def website_analytics(request):
   return render(request, 'admin/analytics.html')


def projects(request, filter=None):
   all_banners = Banner.objects.filter(page=Banner.PROJECTS)
   displayed_banners = choose_banners(all_banners)
   projects = Project.objects.all()
   all_proj_len = len(projects)
   if filter != None:
      filter_umbrella = Project_umbrella.objects.get(short_name=filter)
      projects = filter_umbrella.project_set.all()
   umbrellas = Project_umbrella.objects.all()
   recent_projects = Project.objects.order_by('-id')[:2] # This is a stand in for getting the most recently updated projects
   context = {'projects': projects, 'all_proj_len': all_proj_len, 'banners': displayed_banners, 'recent': recent_projects, 'umbrellas': umbrellas, 'filter': filter, 'debug': settings.DEBUG}
   return render(request, 'website/projects.html', context)

#This is the view for individual projects, rather than the overall projects page
def project_ind(request, project_name):
   project = get_object_or_404(Project, short_name__iexact=project_name)
   all_banners = project.banner_set.all()
   if len(all_banners) == 0:
      all_banners = Banner.objects.all()
   displayed_banners = choose_banners(all_banners)
   members = project.project_role_set.all()
   active_members = []
   publications = project.publication_set.order_by('-date')
   videos = project.video_set.order_by('-date')
   talks = project.talk_set.order_by('-date')
   news = project.news_set.order_by('-date')
   photos = project.photo_set.all()
   alumni =[]
   for member in members:
      if member.is_active():
         active_members.append(member)
      else:
         alumni.append(member)
   active_members.sort(key=operator.attrgetter('start_date'))
   alumni.sort(key=operator.attrgetter('start_date'))
   for role in active_members:
      if role.pi_member == "Co-PI":
         active_members.insert(0, active_members.pop(active_members.index(role)))
   for role in active_members:
      if role.pi_member == "PI":
         active_members.insert(0, active_members.pop(active_members.index(role)))
   for role in alumni:
      if role.pi_member == "Co-PI":
         alumni.insert(0, alumni.pop(alumni.index(role)))
   for role in alumni:
      if role.pi_member == "PI":
         alumni.insert(0, alumni.pop(alumni.index(role)))
   context = {'banners': displayed_banners, 'project': project, 'active': active_members, 'alumni': alumni, 'publications': publications, 'talks': talks, 'videos': videos, 'news': news, 'photos': photos, 'debug':settings.DEBUG}
   return render(request, 'website/indproject.html', context)


def news(request, news_id):
   all_banners = Banner.objects.all()
   displayed_banners = choose_banners(all_banners)
   news = get_object_or_404(News, pk=news_id)
   max_extra_items = 4 # Maximum number of authors 
   all_author_news = news.author.news_set.all()
   author_news = []
   for item in all_author_news:
      if item != news:
         author_news.append(item)
   project_news = {}
   if news.project != None:
      for project in news.project.all():
         ind_proj_news = []
         all_proj_news = project.news_set.all()
         for item in all_proj_news:
            if item != news:
               ind_proj_news.append(item)
         project_news[project] = ind_proj_news[:max_extra_items]
   context = {'banners': displayed_banners, 'news': news, 'author_news': author_news[:max_extra_items], 'project_news': project_news, 'debug': settings.DEBUG}
   return render(request, 'website/news.html', context)
