import operator, datetime, random
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, render
from .models import Person, Publication, Talk, Position, Banner, News, Keyword, Video, Project, Project_umbrella
from django.conf import settings
from operator import itemgetter, attrgetter, methodcaller
from datetime import date

#from . import googleanalytics

max_banners = 7 # TODO: figure out best way to specify these settings... like, is it good to have them up here?
filter_all_pubs_prior_to_date = datetime.date(2012, 1, 1) # Date Makeability Lab was formed

#Every view is passed settings.DEBUG. This is used to insert the appropriate google analytics tracking when in
# production, and to not include it for development
 
def index(request):
    news_items_num = 7 # Defines the number of news items that will be selected
    papers_num = 5 # Defines the number of papers which will be selected
    talks_num = 8 # Defines the number of talks which will be selected
    videos_num = 4 # Defines the number of videos which will be selected
    projects_num = 3 # Defines the number of projects which will be selected

    all_banners = Banner.objects.filter(page=Banner.FRONTPAGE)
    displayed_banners = choose_banners(all_banners)
    print(settings.DEBUG)
    #Select recent news, papers, and talks.
    news_items = News.objects.order_by('-date')[:news_items_num]
    publications = Publication.objects.order_by('-date')[:papers_num]
    talks = Talk.objects.order_by('-date')[:talks_num]
    videos = Video.objects.order_by('-date')[:videos_num]

    if settings.DEBUG:
      projects = Project.objects.all()[:projects_num];
    else:
      projects = sort_popular_projects(googleanalytics.run(get_ind_pageviews))[:projects_num]

    context = { 'people': Person.objects.all(),
                'banners': displayed_banners,
                'news': news_items,
                'publications': publications,
                'talks': talks,
                'videos':videos,
                'projects': projects,
                'debug': settings.DEBUG }
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
    alumni_prof_grad = []
    alumni_prof = []
    alumni_postdoc = []
    alumni_phd = []
    alumni_ms = []
    alumni_undergrad = []
    alumni_highschool = []
    cur_collaborators = []
    past_collaborators = []

    for position in positions:
        if position.is_current_member():
            if position.is_professor() or position.is_grad_student():
                if position.is_professor():
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
           if position.is_professor() or position.is_grad_student():
              if position.is_professor():
                 alumni_prof.append(position)
              elif position.title == Position.POST_DOC:
                 alumni_postdoc.append(position)
              elif position.title == Position.PHD_STUDENT:
                 alumni_phd.append(position)
              elif position.title == Position.MS_STUDENT:
                 alumni_ms.append(position)
           elif position.title == Position.UGRAD:
              alumni_undergrad.append(position)
           elif position.title == Position.HIGH_SCHOOL:
              alumni_highschool.append(position)
        elif position.is_collaborator():
            if position.is_current_collaborator():
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
    alumni_prof.sort(key=operator.attrgetter('end_date'))
    alumni_postdoc.sort(key=operator.attrgetter('end_date'))
    alumni_phd.sort(key=operator.attrgetter('end_date'))
    alumni_ms.sort(key=operator.attrgetter('end_date'))
    alumni_undergrad.sort(key=operator.attrgetter('end_date'))
    alumni_highschool.sort(key=operator.attrgetter('end_date'))
    alumni_members.reverse()
    alumni_prof.reverse()
    alumni_postdoc.reverse()
    alumni_phd.reverse()
    alumni_ms.reverse()
    alumni_undergrad.reverse()
    alumni_highschool.reverse()
    cur_collaborators.sort(key=operator.attrgetter('start_date'))
    past_collaborators.sort(key=operator.attrgetter('end_date'))
    past_collaborators.reverse()

    # merge lists for easier display
    active_prof_grad.extend(active_prof)
    active_prof_grad.extend(active_postdoc)
    active_prof_grad.extend(active_phd)
    active_prof_grad.extend(active_ms)
    alumni_prof_grad.extend(alumni_prof)
    alumni_prof_grad.extend(alumni_postdoc)
    alumni_prof_grad.extend(alumni_phd)
    alumni_prof_grad.extend(alumni_ms)
   
    seen = [] 
    for member in alumni_prof_grad:
       if member.person in seen:
           alumni_prof_grad.remove(member)
       else:
          seen.append(member.person)

    seen = [] 
    for member in alumni_undergrad:
       if member.person in seen:
           alumni_undergrad.remove(member)
       else:
          seen.append(member.person)

    seen = [] 
    for member in alumni_highschool:
       if member.person in seen:
          alumni_highschool.remove(member)
       else:
          seen.append(member.person)
    
    alumni_members.extend(alumni_prof_grad)
    alumni_members.extend(alumni_undergrad)
    alumni_members.extend(alumni_highschool)

    seen = []
    for member in alumni_members:
       if member.person in seen:
          alumni_members.remove(member)
       else:
          seen.append(member.person)

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
        'alumni_prof_grad': alumni_prof_grad,
        'alumni_prof' : alumni_prof,
        'alumni_postdoc' : alumni_postdoc,
        'alumni_phd' : alumni_phd,
        'alumni_ms' : alumni_ms,
        'alumni_undergrad' : alumni_undergrad,
        'alumni_highschool' : alumni_highschool,
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
   context = { 'person': person,
               'news': news,
               'talks': talks,
               'publications': publications,
               'banners': displayed_banners,
               'debug': settings.DEBUG }
   return render(request, 'website/member.html', context)

def publications(request):
    all_banners = Banner.objects.filter(page=Banner.PUBLICATIONS)
    displayed_banners = choose_banners(all_banners)
    filter = request.GET.get('filter', None)
    groupby = request.GET.get('groupby', "No-Group")

    # We want all pubs after I joined as a professor. This was a group decision.
    # See https://stackoverflow.com/a/4668703
    # sampledate__gte=datetime.date(2011, 1, 1),
    # Old: Publication.objects.filter(date__range=["2012-01-01", date.today()]),
    context = { 'publications': Publication.objects.filter(date__gte=filter_all_pubs_prior_to_date),
                'banners': displayed_banners,
                'filter': filter,
                'groupby': groupby,
                'debug': settings.DEBUG }
    return render(request, 'website/publications.html', context)

def talks(request):
    all_banners = Banner.objects.filter(page=Banner.TALKS)
    displayed_banners = choose_banners(all_banners)
    filter = request.GET.get('filter', None)
    groupby = request.GET.get('groupby', "No-Group")
    context = { 'talks': Talk.objects.filter(date__gte=filter_all_pubs_prior_to_date),
                'banners': displayed_banners,
                'filter': filter,
                'groupby': groupby,
                'debug': settings.DEBUG }
    return render(request, 'website/talks.html', context)

def website_analytics(request):
   return render(request, 'admin/analytics.html')
      
def projects(request):
   all_banners = Banner.objects.filter(page=Banner.PROJECTS)
   displayed_banners = choose_banners(all_banners)
   projects = Project.objects.all()
   all_proj_len = len(projects)
   filter = request.GET.get('filter')
   if filter != None:
      filter_umbrella = Project_umbrella.objects.get(short_name=filter)
      projects = filter_umbrella.project_set.all()
   umbrellas = Project_umbrella.objects.all()
   popular_projects = sort_popular_projects(googleanalytics.run(get_ind_pageviews))[:4]
   recent_projects = get_most_recent(Project.objects.order_by('-updated'))[:2]
   context = { 'projects': projects,
               'all_proj_len': all_proj_len,
               'banners': displayed_banners,
               'recent': recent_projects,
               'popular': popular_projects,
               'umbrellas': umbrellas,
               'filter': filter,
               'debug': settings.DEBUG}
   return render(request, 'website/projects.html', context)

# This is the view for individual projects, rather than the overall projects page
def project_ind(request, project_name):
   project = get_object_or_404(Project, short_name__iexact=project_name)
   all_banners = project.banner_set.all()
   displayed_banners = choose_banners(all_banners)
   project_members = project.project_role_set.order_by('start_date')
   current_members = [] # = project_members.filter(is_active=True) # can't use is_active in filter because it's a function
   alumni_members = [] # = project_members.filter(is_active=False).order_by('end_date')

   for member in project_members:
       if member.is_active():
           current_members.append(member)
       else:
           alumni_members.append(member)

   #TODO: sort current members by PI, Co-PI first, then start date (oldest start date first), then role (e.g., professors, then grad, then undergrad),
   #TODO: sorty alumni members by PI, CO-PI first, then date date (most recent end date first), then role
   alumni_members = sorted(alumni_members, key=attrgetter('end_date'), reverse=True)

   publications = project.publication_set.order_by('-date')
   videos = project.video_set.order_by('-date')
   talks = project.talk_set.order_by('-date')
   news = project.news_set.order_by('-date')
   photos = project.photo_set.all()
   project_members_dict = {
       'Current Project Members' : current_members,
       'Past Project Members' : alumni_members
   }

   context = { 'banners': displayed_banners,
               'project': project,
               'project_members' : project_members,
               'project_members_dict' : project_members_dict,
               'publications': publications,
               'talks': talks,
               'videos': videos,
               'news': news,
               'photos': photos,
               'debug': settings.DEBUG}

   return render(request, 'website/indproject.html', context)


def news(request, news_id):
   all_banners = Banner.objects.filter(page=Banner.FRONTPAGE)
   displayed_banners = choose_banners(all_banners)
   news = get_object_or_404(News, pk=news_id)
   max_extra_items = 4 # Maximum number of authors 
   all_author_news = news.author.news_set.order_by('-date')
   author_news = []
   for item in all_author_news:
      if item != news:
         author_news.append(item)
   project_news = {}
   if news.project != None:
      for project in news.project.all():
         ind_proj_news = []
         all_proj_news = project.news_set.order_by('-date')
         for item in all_proj_news:
            if item != news:
               ind_proj_news.append(item)
         project_news[project] = ind_proj_news[:max_extra_items]

   context = { 'banners': displayed_banners,
               'news': news,
               'author_news': author_news[:max_extra_items],
               'project_news': project_news,
               'debug': settings.DEBUG }
   return render(request, 'website/news.html', context)

## Helper functions for views ##

def get_most_recent(projects):
   updated = []
   print(projects)
   for project in projects:
      #Adding more times to the time array will allow you to add additional fields in the future
      times = []
      if project.updated != None:
         times.append(project.updated)
      if len(project.publication_set.all()) > 0:
         times.append(project.publication_set.order_by('-date')[0].date)
      if len(project.talk_set.all()) > 0:
         times.append(project.talk_set.order_by('-date')[0].date)
      if len(project.video_set.all()) > 0:
         times.append(project.video_set.order_by('-date')[0].date)
      times.sort()
      updated.append({'proj': project, 'updated': times[0]})
   sorted_list = sorted(updated, key=lambda k: k['updated'], reverse=True)
   return [item['proj'] for item in sorted_list]

#Get the page views per page including their first and second level paths
def get_ind_pageviews(service, profile_id):
  return service.data().ga().get(
    ids='ga:' + profile_id,
    start_date='30daysAgo',
    end_date='today',
    metrics='ga:pageviews',
    dimensions='ga:PagePathLevel1,ga:PagePathLevel2'
  ).execute().get('rows')

def get_project(page):
   proj = None
   for project in Project.objects.all():
      if project.short_name in page.lower():
         proj = project
   return proj

def sort_popular_projects(projects):
   page_views = {}
   for path, subpage, count in projects:
      if 'project' in path:
         proj=get_project(subpage)
         if proj != None:
            if proj in page_views.keys():
               page_views[proj]+=int(count)
            else:
               page_views[proj]=int(count)
   project_popularity=sorted([{'proj': key, 'views': page_views[key]} for key in page_views.keys()], key=lambda k: k['views'], reverse=True)
   return [item['proj'] for item in project_popularity]

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

def choose_banners_helper(banners, count):
    banner_weights = []
    total_weight = 0
    for banner in banners:
        elapsed = (datetime.datetime.now().date() - banner.date_added).days / 31.0
        if elapsed <= 0:
            elapsed = 1.0 / 31.0
        weight = 1.0 + 1.0 / elapsed
        banner_weights.append((banner, weight))
        total_weight += weight
    for i in range(0, len(banner_weights)):
        banner_weights[i] = (banner_weights[i][0], banner_weights[i][1] / total_weight)
        print(banner_weights[i][1])

    selected_banners = []
    for i in range(0, count):
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

def choose_banners(banners):
  favorite_banners = []
  other_banners = []
  for banner in banners:
    if banner.favorite == True:
      favorite_banners.append(banner)
    else:
      other_banners.append(banner)

  selected_banners = choose_banners_helper(favorite_banners, max_banners)
  if len(selected_banners) < max_banners:
    temp = choose_banners_helper(other_banners, max_banners - len(selected_banners))
    for banner in temp:
      selected_banners.append(banner)

  return selected_banners
