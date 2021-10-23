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
import logging

from django.http import Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from website.serializers import TalkSerializer, PublicationSerializer

from django.http import Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from website.serializers import TalkSerializer, PublicationSerializer, PersonSerializer, ProjectSerializer, VideoSerializer, NewsSerializer

max_banners = 7  # TODO: figure out best way to specify these settings... like, is it good to have them up here?
filter_all_pubs_prior_to_date = datetime.date(2012, 1, 1)  # Date Makeability Lab was formed

_logger = logging.getLogger(__name__)


class TalkList(APIView):
    '''
    List all talks, or create a new talk
    '''

    def get(self, request, format=None):
        talks = Talk.objects.all()
        serializer = TalkSerializer(talks, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request, format=None):
        serializer = TalkSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TalkDetail(APIView):
    """
    Retrieve, update or delete a snippet instance.
    """

    def get_object(self, pk):
        try:
            return Talk.objects.get(pk=pk)
        except Talk.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        talk = self.get_object(pk)
        serializer = TalkSerializer(talk)
        return Response(serializer.data)

    def put(self, request, pk, format=None):
        talk = self.get_object(pk)
        serializer = TalkSerializer(talk, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, format=None):
        talk = self.get_object(pk)
        talk.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PubsList(APIView):
    '''
    List all talks, or create a new talk
    '''

    def get(self, request, format=None):
        pubs = Publication.objects.all()
        serializer = PublicationSerializer(pubs, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request, format=None):
        serializer = PublicationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PubsDetail(APIView):
    """
    Retrieve, update or delete a snippet instance.
    """

    def get_object(self, pk):
        try:
            return Publication.objects.get(pk=pk)
        except Publication.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        pub = self.get_object(pk)
        serializer = PublicationSerializer(pub)
        return Response(serializer.data)

    def put(self, request, pk, format=None):
        pub = self.get_object(pk)
        serializer = PublicationSerializer(pub, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, format=None):
        pub = self.get_object(pk)
        pub.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PersonList(APIView):
    '''
    List all talks, or create a new talk
    '''

    def get(self, request, format=None):
        people = Person.objects.all()
        serializer = PersonSerializer(people, many=True, context={'request': request})
        return Response(serializer.data)


class PersonDetail(APIView):
    """
    Retrieve, update or delete a snippet instance.
    """

    def get_object(self, pk):
        try:
            return Person.objects.get(pk=pk)
        except Person.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        person = self.get_object(pk)
        serializer = PersonSerializer(person)
        return Response(serializer.data)


class NewsList(APIView):
    '''
    List all talks, or create a new talk
    '''

    def get(self, request, format=None):
        news = News.objects.all()
        serializer = NewsSerializer(news, many=True, context={'request': request})
        return Response(serializer.data)


class NewsDetail(APIView):
    """
    Retrieve, update or delete a snippet instance.
    """

    def get_object(self, pk):
        try:
            return News.objects.get(pk=pk)
        except News.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        news = self.get_object(pk)
        serializer = NewsSerializer(person)
        return Response(serializer.data)


class VideoList(APIView):
    '''
    List all talks, or create a new talk
    '''

    def get(self, request, format=None):
        videos = Video.objects.all()
        serializer = VideoSerializer(videos, many=True, context={'request': request})
        return Response(serializer.data)


class VideoDetail(APIView):
    """
    Retrieve, update or delete a snippet instance.
    """

    def get_object(self, pk):
        try:
            return Video.objects.get(pk=pk)
        except Video.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        video = self.get_object(pk)
        serializer = VideoSerializer(video)
        return Response(serializer.data)


class ProjectList(APIView):
    '''
    List all talks, or create a new talk
    '''

    def get(self, request, format=None):
        projects = Project.objects.all()
        serializer = ProjectSerializer(projects, many=True, context={'request': request})
        return Response(serializer.data)


class ProjectDetail(APIView):
    """
    Retrieve, update or delete a snippet instance.
    """

    def get_object(self, pk):
        try:
            return Project.objects.get(pk=pk)
        except Project.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        project = self.get_object(pk)
        serializer = ProjectSerializer(project)
        return Response(serializer.data)


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
    projects = sort_projects_by_most_recent_pub(projects, settings.DEBUG)

    # we used to only filter out incomplete projects if DEBUG = TRUE; if not settings.DEBUG:
    projects = filter_incomplete_projects(projects)

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
    persons = Person.objects.all()
    map_status_to_title_to_people = dict()
    map_status_to_headers = dict()
    map_header_text_to_header_name = dict()
    map_status_to_num_people = dict()

    for person in persons:
        position = person.get_latest_position()

        if position is not None:


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

    # now go through these dicts and sort people by dates
    for status, map_title_to_people in map_status_to_title_to_people.items():
        for title, people_with_title in map_title_to_people.items():
            if "Current" in status:
                # sort current members and collaborators by start date first (so
                # people who started earliest are shown first)
                # people_with_title.sort(key=operator.attrgetter('start_date'))

                # sort people by their earliest position in the current role
                people_with_title.sort(key=lambda pos: (
                    pos.person.get_earliest_position_in_role(pos.role).start_date
                ))
            else:
                # sort past members and collaborators reverse chronologically by end date (so people
                # who ended most recently are shown first)
                people_with_title.sort(key=operator.attrgetter('end_date'), reverse=True)

    sorted_titles = Position.get_sorted_titles()

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
        'map_header_text_to_header_name': map_header_text_to_header_name,
        'sorted_titles': sorted_titles,
        'positions': Position.objects.all(),
        'banners': displayed_banners,
        'debug': settings.DEBUG
    }
    return render(request, 'website/people.html', context)


def member(request, member_id):
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
    project_roles = person.project_role_set.order_by('start_date')
    projects = person.get_projects()

    # filter projects to those that have a thumbnail and have been published
    filtered_projects = list()
    for proj in projects:
        if proj.gallery_image is not None and proj.has_publication():
            filtered_projects.append(proj)
    projects = filtered_projects

    context = {'person': person,
               'news': news,
               'talks': talks,
               'publications': publications,
               'project_roles': project_roles,
               'projects' : projects,
               'banners': displayed_banners,
               'debug': settings.DEBUG,
               'page_title': person.get_full_name()}
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
    context = {'talks': Talk.objects.filter(date__gte=filter_all_pubs_prior_to_date).order_by('-date'),
               'banners': displayed_banners,
               'filter': filter,
               'groupby': groupby,
               'debug': settings.DEBUG}
    return render(request, 'website/talks.html', context)


def videos(request):
    all_banners = Banner.objects.filter(page=Banner.VIDEOS)
    displayed_banners = choose_banners(all_banners)
    filter = request.GET.get('filter', None)
    groupby = request.GET.get('groupby', "No-Group")
    context = {'videos': Video.objects.filter(date__range=["2012-01-01", date.today()]).order_by('-date'),
               'banners': displayed_banners,
               'filter': filter,
               'groupby': groupby,
               'debug': settings.DEBUG}
    return render(request, 'website/videos.html', context)


def website_analytics(request):
    return render(request, 'admin/analytics.html')


def projects(request):
    """
    Creates the render context for the project gallery page.
    :param request:
    :return:
    """
    all_banners = Banner.objects.filter(page=Banner.PROJECTS)
    displayed_banners = choose_banners(all_banners)
    projects = Project.objects.all()

    # Only show projects that have a thumbnail, description, and a publication
    # we used to only filter out incomplete projects if DEBUG = TRUE; if not settings.DEBUG:
    projects = filter_incomplete_projects(projects)

    # if we are in debug mode, we include all projects even if they have no artifacts
    # as long as they have a start date
    ordered_projects = sort_projects_by_most_recent_pub(projects, settings.DEBUG)

    context = {'projects': ordered_projects,
               'banners': displayed_banners,
               'filter': filter,
               'debug': settings.DEBUG}
    return render(request, 'website/projects.html', context)


def project(request, project_name):
    """
    This is the view for *individual* project pages rather than the project page gallery
    :param request:
    :param project_name:
    :return:
    """
    project = get_object_or_404(Project, short_name__iexact=project_name)
    all_banners = project.banner_set.all()
    displayed_banners = choose_banners(all_banners)

    publications = project.publication_set.order_by('-date')
    videos = project.video_set.order_by('-date')
    talks = project.talk_set.order_by('-date')
    news = project.news_set.order_by('-date')
    photos = project.photo_set.all()

    # A Project_Role object has a person, role (open text field), start_date, end_date
    project_roles = project.project_role_set.order_by('start_date')

    # Sort project roles by start date and then title (e.g., professors first) and then last name
    project_roles = sorted(project_roles, key=lambda pr: (pr.start_date, pr.get_pi_status_index(), pr.person.get_current_title_index(), pr.person.last_name))

    project_roles_current = []
    project_roles_past = []

    for project_role in project_roles:
        if project_role.is_active():
            project_roles_current.append(project_role)
        else:
            project_roles_past.append(project_role)

    project_roles_past = sorted(project_roles_past, key=attrgetter('end_date'), reverse=True)

    map_status_to_title_to_project_role = dict()

    for project_role in project_roles:
        person = project_role.person

        position = person.get_latest_position()
        if position is not None:
            title = position.title
            if "Professor" in position.title:  # necessary to collapse all prof categories to 1
                title = "Professor"

            # check for current status on project
            member_status_name = Position.PAST_MEMBER
            if project_role.is_active():
                member_status_name = Position.CURRENT_MEMBER

            if member_status_name not in map_status_to_title_to_project_role:
                map_status_to_title_to_project_role[member_status_name] = dict()

            if title not in map_status_to_title_to_project_role[member_status_name]:
                map_status_to_title_to_project_role[member_status_name][title] = list()

            map_status_to_title_to_project_role[member_status_name][title].append(project_role)

    for status, map_title_to_project_role in map_status_to_title_to_project_role.items():
        for title, project_role_with_title in map_title_to_project_role.items():
            if "Current" in status:
                # sort current members and collaborators by start date first (so
                # people who started earliest are shown first)
                project_role_with_title.sort(key=operator.attrgetter('start_date'))
            else:
                # sort past members and collaborators reverse chronologically by end date (so people
                # who ended most recently are shown first)
                project_role_with_title.sort(key=operator.attrgetter('end_date'), reverse=True)

    # TODO: While we likely want current members sorted by titles, I think it makes the most sense
    #       to sort previous members by most recent first (and ignore title)... but I'm not sure
    sorted_titles = Position.get_sorted_titles()

    map_status_to_title_to_people = map_status_to_title_to_project_role

    context = {'banners': displayed_banners,
               'project': project,
               'project_roles': project_roles,
               'project_roles_current': project_roles_current,
               'project_roles_past': project_roles_past,
               'map_status_to_title_to_project_role': map_status_to_title_to_project_role,
               'map_status_to_title_to_people': map_status_to_title_to_people,
               'sorted_titles': sorted_titles,
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
    all_banners = Banner.objects.filter(page=Banner.NEWSLISTING)
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

def faq(request):
    all_banners = Banner.objects.filter(page=Banner.PEOPLE)
    displayed_banners = choose_banners(all_banners)
    context = {'banners': displayed_banners,
               'debug': settings.DEBUG}
    return render(request, "website/faq.html", context)

def filter_incomplete_projects(projects):
    '''
    Filters out projects that don't have thumbnails, publications, an about information
    :param projects:
    :return:
    '''
    filtered = list()
    for project in projects:
        # I tested this and if project.about or project.gallery_image are not set,
        # they will be interpreted as False by Python
        if project.has_publication() and project.about and project.gallery_image:
            filtered.append(project)

    return filtered


'''
def filter_no_pubs_projects(projects):
    filtered = []
    for project in projects:
        if len(project.publication_set.all()) > 0:
            filtered.append(project)
    return filtered
'''


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


## Helper functions for views ##
def sort_projects_by_most_recent_pub(projects, include_projects_with_no_artifacts=False):
    return sort_projects_by_most_recent_artifact(projects, include_projects_with_no_artifacts,
                                                 only_look_at_pubs=True)

def sort_projects_by_most_recent_artifact(projects, include_projects_with_no_artifacts=False,
                                          only_look_at_pubs=True):
    """Sorts projects by most recent artifact
    :return: a sorted list of projects by most recent artifact date"""
    # print(projects)
    sorted_projects = list()
    for project in projects:

        # most_recent_artifact is a tuple of (date, artifact)
        most_recent_artifact = project.get_most_recent_artifact()

        # get most recent pub. use this instead
        if only_look_at_pubs:
            most_recent_pub = project.get_most_recent_publication()
            if most_recent_pub is not None:
                most_recent_artifact = (most_recent_pub.date, most_recent_pub)
            else:
                most_recent_artifact = None

        # _logger.debug("The most recent artifact: ", str(most_recent_artifact))
        if most_recent_artifact is not None:
            project_date_tuple = (project, most_recent_artifact[0])
            sorted_projects.append(project_date_tuple)
        elif include_projects_with_no_artifacts and project.start_date is not None:
            sorted_projects.append((project, project.start_date))

    # sort the artifacts by date
    sorted_projects = sorted(sorted_projects, key=itemgetter(1), reverse=True)
    _logger.warning("Hello!")
    print(__name__)
    for project_tuple in sorted_projects:
        _logger.debug("Project: " + str(project_tuple[0]) + " Most recent modification date: " + str(project_tuple[1]))

    ordered_projects = []
    if len(sorted_projects) > 0:
        ordered_projects, temp = zip(*sorted_projects)

    return ordered_projects