# Django 4+ removed django.conf.urls.url()
# https://stackoverflow.com/a/70319607
# from django.conf.urls import url
from django.urls import re_path

from . import views
from rest_framework.urlpatterns import format_suffix_patterns

app_name = 'website'
urlpatterns = [
    re_path(r'^$', views.index, name='index'),
    re_path(r'^people/$', views.people, name='people'),
    re_path(r'^member/(?P<member_id>[0-9]+)/$', views.member, name='member'),
    re_path(r'^member/(?P<member_id>[-a-z]+)/$', views.member, name='member'),
    re_path(r'^publications/$', views.publications, name='publications'),
    re_path(r'^talks/$', views.talks, name='talks'),
    re_path(r'^videos/$', views.videos, name='videos'),
    re_path(r'^projects/$', views.projects, name='projects'),
    re_path(r'^projects/(?P<project_name>[a-zA-Z ]+)/$', views.project, name='project'),
    re_path(r'^project/(?P<project_name>[a-zA-Z ]+)/$', views.project, name='project'),
    re_path(r'^news/$', views.news_listing, name='news_listing'),
    re_path(r'^news/(?P<news_id>[0-9]+)/$', views.news, name='news'),
    re_path(r'^faq/$', views.faq, name='faq'),
    
    # JEF (Oct 31, 2022): this makes it sound you can just type in a project name
    # and we'll try to go to that project without putting in 'projects' or 'project'
    # For example, http://makeabilitylab.cs.uw.edu/soundwatch will go to
    # http://makeabilitylab.cs.uw.edu/project/soundwatch 
    #
    # Update: had to remove this as it prevented us from going to the admin page, oops!
    # Needs more thought.
    #re_path(r'(?P<project_name>[a-zA-Z ]+)/$', views.redirect_project, name='project'),
]

urlpatterns = format_suffix_patterns(urlpatterns)