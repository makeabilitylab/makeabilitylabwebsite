from django.conf import settings # for access to settings variables, see https://docs.djangoproject.com/en/4.0/topics/settings/#using-settings-in-python-code
from website.models import Banner, Person
import website.utils.ml_utils as ml_utils 
from django.shortcuts import render, get_object_or_404

def member(request, member_id):
    news_items_num = 5  # Defines the number of news items that will be selected
    all_banners = Banner.objects.filter(page=Banner.PEOPLE)
    displayed_banners = ml_utils.choose_banners(all_banners)

    # TODO: what is this set of code for?
    # get_object_or_404 is a Django shortcut that raises Http404 instead of the model’s DoesNotExist exception
    # https://docs.djangoproject.com/en/4.0/topics/http/shortcuts/#get-object-or-404
    if (member_id.isdigit()):
        person = get_object_or_404(Person, pk=member_id)
    else:
        person = get_object_or_404(Person, url_name__iexact=member_id)

    # Get objects relevant to this person
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

    # Render is a Django shortcut (aka helper function). It combines a given template—in this case
    # member.html—with a context dictionary and returns an HttpResponse object with that rendered text.
    # See: https://docs.djangoproject.com/en/4.0/topics/http/shortcuts/#render
    return render(request, 'website/member.html', context)