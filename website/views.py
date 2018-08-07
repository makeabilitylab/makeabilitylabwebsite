import operator, datetime, random
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, render
from .models import Person, Publication, Talk, Position, Banner, News, Keyword, Video, Project, Project_umbrella
from django.conf import settings
from operator import itemgetter, attrgetter, methodcaller
from datetime import date
import datetime
from django.utils.timezone import utc
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

# The Google Analytics stuff is all broken now. It was originally used to track the popularity
# of pages, projects, and downloads. Not sure what we should do with it now.
# from . import googleanalytics

max_banners = 7  # TODO: figure out best way to specify these settings... like, is it good to have them up here?
filter_all_pubs_prior_to_date = datetime.date(2012, 1, 1)  # Date Makeability Lab was formed


# Every view is passed settings.DEBUG. This is used to insert the appropriate google analytics tracking when in
# production, and to not include it for development

def index(request):
    news_items_num = 7  # Defines the number of news items that will be selected
    papers_num = 10  # Defines the number of papers which will be selected
    talks_num = 8  # Defines the number of talks which will be selected
    videos_num = 4  # Defines the number of videos which will be selected
    projects_num = 3  # Defines the number of projects which will be selected

    all_banners = Banner.objects.filter(page=Banner.FRONTPAGE)
    displayed_banners = choose_banners(all_banners)
    print(settings.DEBUG)
    # Select recent news, papers, and talks.
    news_items = News.objects.order_by('-date')[:news_items_num]
    publications = Publication.objects.order_by('-date')[:papers_num]
    talks = Talk.objects.order_by('-date')[:talks_num]
    videos = Video.objects.order_by('-date')[:videos_num]

    # if settings.DEBUG:
    #   projects = Project.objects.all()[:projects_num];
    # else:
    #   # Return projects based on Google Analytics popularity
    #   projects = sort_popular_projects(googleanalytics.run(get_ind_pageviews))[:projects_num]

    # Sort projects by recency of publication
    # projects = Project.objects.all()
    # sorted(projects, key=lambda project: student[2])
    projects = Project.objects.all()
    projects = get_most_recent(projects);
    projects = filter_projects(projects);

    context = {'people': Person.objects.all(),
               'banners': displayed_banners,
               'news': news_items,
               'publications': publications,
               'talks': talks,
               'videos': videos,
               'projects': projects,
               'debug': settings.DEBUG}

    return render(request, 'website/index.html', context)


def people(request):
    positions = Position.objects.all()
    map_status_to_title_to_people = dict()
    map_status_to_headers = dict()
    map_header_text_to_header_name = dict()
    map_status_to_num_people = dict()

    for position in positions:
        title = position.title
        if "Professor" in position.title:  # necessary to collapse all prof categories to 1
            title = "Professor"

        member_status_name = ""
        if position.is_current_member():
            member_status_name = Position.CURRENT_MEMBER
        elif position.is_alumni_member():
            member_status_name = Position.PAST_MEMBER
        elif position.is_current_collaborator():
            member_status_name = Position.CURRENT_COLLABORATOR
        elif position.is_past_collaborator():
            member_status_name = Position.PAST_COLLABORATOR

        if member_status_name not in map_status_to_title_to_people:
            map_status_to_title_to_people[member_status_name] = dict()

        if title not in map_status_to_title_to_people[member_status_name]:
            map_status_to_title_to_people[member_status_name][title] = list()

        map_status_to_title_to_people[member_status_name][title].append(position)

    for status, map_title_to_people in map_status_to_title_to_people.items():
        for title, people_with_title in map_title_to_people.items():
            if "Current" in status:
                # sort current members and collaborators by start date first (so
                # people who started earliest are shown first)
                people_with_title.sort(key=operator.attrgetter('start_date'))
            else:
                # sort past members and collaborators reverse chronologically by end date (so people
                # who ended most recently are shown first)
                people_with_title.sort(key=operator.attrgetter('end_date'), reverse=True)

    sorted_titles = ("Professor", Position.RESEARCH_SCIENTIST, Position.POST_DOC, Position.SOFTWARE_DEVELOPER,
                     Position.PHD_STUDENT, Position.MS_STUDENT, Position.UGRAD, Position.HIGH_SCHOOL)

    # Professors can't be past members, so deal with this case
    if Position.PAST_MEMBER in map_status_to_title_to_people and \
            "Professor" in map_status_to_title_to_people[Position.PAST_MEMBER]:
        del map_status_to_title_to_people[Position.PAST_MEMBER]["Professor"]

    # to avoid getting errors when there are no people in these categories, set our defaults
    positionNames = [Position.CURRENT_MEMBER, Position.CURRENT_COLLABORATOR, Position.PAST_MEMBER,
                     Position.PAST_COLLABORATOR]
    for position in positionNames:
        map_status_to_headers[position] = dict()
        map_status_to_headers[position]["subHeader"] = "None"
        map_status_to_headers[position]["headerText"] = list()


    # setup headers
    for status, map_title_to_people in map_status_to_title_to_people.items():
        if status not in map_status_to_headers:
            map_status_to_headers[status] = dict()


        # get the subHeaders, headerTexts, and headerNames
        map_status_to_headers[status]["subHeader"] = ""
        map_status_to_headers[status]["headerText"] = list()
        map_status_to_num_people[status] = 0

        need_comma = False
        for title in sorted_titles:
            if title in map_title_to_people and len(map_title_to_people[title]) > 0:
                if need_comma:
                    map_status_to_headers[status]["subHeader"] += ", "

                header = title + " (" + str(len(map_title_to_people[title])) + ")"
                print(title)
                map_status_to_headers[status]["subHeader"] += header
                map_status_to_headers[status]["headerText"].append(header)
                map_header_text_to_header_name[title + " (" + str(len(map_title_to_people[title])) + ")"] = title
                map_status_to_num_people[status] += len(map_title_to_people[title])
                need_comma = True

    all_banners = Banner.objects.filter(page=Banner.PEOPLE)
    displayed_banners = choose_banners(all_banners)

    context = {
        'people': Person.objects.all(),
        'map_status_to_title_to_people': map_status_to_title_to_people,
        'map_status_to_num_people': map_status_to_num_people,
        'map_status_to_headers': map_status_to_headers,
        'map_header_text_to_header_name':  map_header_text_to_header_name,
        'sorted_titles': sorted_titles,
        'positions': positions,
        'banners': displayed_banners,
        'debug': settings.DEBUG
    }
    return render(request, 'website/people.html', context)


def member(request, member_id):
    # try:
    #     person = Person.objects.get(pk=member_id)
    # except Person.DoesNotExist:
    #     raise Http404("Person does not exist")
    # return render(request, 'website/member.html', {'person': person})
    news_items_num = 5  # Defines the number of news items that will be selected
    all_banners = Banner.objects.filter(page=Banner.PEOPLE)
    displayed_banners = choose_banners(all_banners)

    if (member_id.isdigit()):
        person = get_object_or_404(Person, pk=member_id)
    else:
        person = get_object_or_404(Person, url_name__iexact=member_id)

    news = person.news_set.order_by('-date')[:news_items_num]
    publications = person.publication_set.order_by('-date')
    talks = person.talk_set.order_by('-date')
    context = {'person': person,
               'news': news,
               'talks': talks,
               'publications': publications,
               'banners': displayed_banners,
               'debug': settings.DEBUG}
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
    context = {'publications': Publication.objects.filter(date__gte=filter_all_pubs_prior_to_date),
               'banners': displayed_banners,
               'filter': filter,
               'groupby': groupby,
               'debug': settings.DEBUG}
    return render(request, 'website/publications.html', context)


def talks(request):
    all_banners = Banner.objects.filter(page=Banner.TALKS)
    displayed_banners = choose_banners(all_banners)
    filter = request.GET.get('filter', None)
    groupby = request.GET.get('groupby', "No-Group")
    context = {'talks': Talk.objects.filter(date__gte=filter_all_pubs_prior_to_date),
               'banners': displayed_banners,
               'filter': filter,
               'groupby': groupby,
               'debug': settings.DEBUG}
    return render(request, 'website/talks.html', context)


def videos(request):
    all_banners = Banner.objects.filter(page=Banner.TALKS)
    displayed_banners = choose_banners(all_banners)
    filter = request.GET.get('filter', None)
    groupby = request.GET.get('groupby', "No-Group")
    context = {'videos': Video.objects.filter(date__range=["2012-01-01", date.today()]), 'banners': displayed_banners,
               'filter': filter, 'groupby': groupby, 'debug': settings.DEBUG}
    return render(request, 'website/videos.html', context)


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
    popular_projects = []  # sort_popular_projects(googleanalytics.run(get_ind_pageviews))[:4]
    recent_projects = get_most_recent(Project.objects.order_by('-updated'))[:2]

    context = {'projects': projects,
               'all_proj_len': all_proj_len,
               'banners': displayed_banners,
               'recent': recent_projects,
               'popular': popular_projects,
               'umbrellas': umbrellas,
               'filter': filter,
               'debug': settings.DEBUG}
    return render(request, 'website/projects.html', context)


# This is the view for individual projects, rather than the overall projects page
def project(request, project_name):
    project = get_object_or_404(Project, short_name__iexact=project_name)
    all_banners = project.banner_set.all()
    displayed_banners = choose_banners(all_banners)
    project_members = project.project_role_set.order_by('start_date')
    current_members = []  # = project_members.filter(is_active=True) # can't use is_active in filter because it's a function
    alumni_members = []  # = project_members.filter(is_active=False).order_by('end_date')

    for member in project_members:
        if member.is_active():
            current_members.append(member)
        else:
            if member.is_past():
                alumni_members.append(member)

    # TODO: sort current members by PI, Co-PI first, then start date (oldest start date first), then role (e.g., professors, then grad, then undergrad),
    # TODO: sorty alumni members by PI, CO-PI first, then date date (most recent end date first), then role
    alumni_members = sorted(alumni_members, key=attrgetter('end_date'), reverse=True)

    publications = project.publication_set.order_by('-date')
    videos = project.video_set.order_by('-date')
    talks = project.talk_set.order_by('-date')
    news = project.news_set.order_by('-date')
    photos = project.photo_set.all()
    project_members_dict = {
        'Current Project Members': current_members,
        'Past Project Members': alumni_members
    }

    context = {'banners': displayed_banners,
               'project': project,
               'project_members': project_members,
               'project_members_dict': project_members_dict,
               'publications': publications,
               'talks': talks,
               'videos': videos,
               'news': news,
               'photos': photos,
               'debug': settings.DEBUG}

    return render(request, 'website/project.html', context)


def news_listing(request):
    all_banners = Banner.objects.filter(page=Banner.FRONTPAGE)
    displayed_banners = choose_banners(all_banners)
    filter = request.GET.get('filter', None)
    groupby = request.GET.get('groupby', "No-Group")
    now = datetime.datetime.utcnow().replace(tzinfo=utc)
    news_list = News.objects.all()

    # start the paginator on the first page
    page = request.GET.get('page', 1)

    # change the int parameter below to control the amount of objects displayed on a page
    paginator = Paginator(news_list, 10)
    try:
        news = paginator.page(page)
    except PageNotAnInteger:
        news = paginator.page(1)
    except EmptyPage:
        news = paginator.page(paginator.num_pages)

    context = {'news': news,
               'banners': displayed_banners,
               'filter': filter,
               'groupby': groupby,
               'time_now': now,
               'debug': settings.DEBUG}
    return render(request, 'website/news-listing.html', context)


def news(request, news_id):
    all_banners = Banner.objects.filter(page=Banner.FRONTPAGE)
    displayed_banners = choose_banners(all_banners)
    news = get_object_or_404(News, pk=news_id)
    max_extra_items = 4  # Maximum number of authors
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

    context = {'banners': displayed_banners,
               'news': news,
               'author_news': author_news[:max_extra_items],
               'project_news': project_news,
               'debug': settings.DEBUG}
    return render(request, 'website/news.html', context)


## Helper functions for views ##
def get_most_recent(projects):
    updated = []
    print(projects)
    for project in projects:
        # Adding more times to the time array will allow you to add additional fields in the future
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

    # DEBUG
    for item in sorted_list:
        mostRecentArtifact = item['proj'].get_most_recent_artifact();
        if mostRecentArtifact is not None:
            print(
                "project '{}' has the most recent artifact of {} updated {} and the check {}".format(item['proj'].name,
                                                                                                     mostRecentArtifact,
                                                                                                     mostRecentArtifact.date,
                                                                                                     item['updated']))
        else:
            print("mostRecentArtifact is none")
    # END DEBUG

    return [item['proj'] for item in sorted_list]

def filter_projects(projects):
    filtered = []
    for project in projects:
        if len(project.publication_set.all()) > 0:
            filtered.append(project)
    return filtered

# Get the page views per page including their first and second level paths
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
            proj = get_project(subpage)
            if proj != None:
                if proj in page_views.keys():
                    page_views[proj] += int(count)
                else:
                    page_views[proj] = int(count)
    project_popularity = sorted([{'proj': key, 'views': page_views[key]} for key in page_views.keys()],
                                key=lambda k: k['views'], reverse=True)
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
