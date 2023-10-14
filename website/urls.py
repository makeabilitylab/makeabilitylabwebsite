# Django 4+ removed django.conf.urls.url()
# https://stackoverflow.com/a/70319607
# from django.conf.urls import url
from django.urls import re_path, path

from . import views
from rest_framework.urlpatterns import format_suffix_patterns

# Need to import admin because we now have "lazy" loading where
# we try to go to a project page if someone puts http://makeabilitylab.cs.uw.edu/soundwatch
# then website will try to load http://makeabilitylab.cs.uw.edu/project/soundwatch 
from django.contrib import admin

app_name = 'website'
urlpatterns = [
    re_path(r"^admin/", admin.site.urls),
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

    # First try to match on the news id (for historical compatibility) then match on the slug
    path('news/<int:id>/', views.news, name='news_item_by_id'),
    path('news/<slug:slug>/', views.news, name='news_item_by_slug'),
    
    re_path(r'^faq/$', views.faq, name='faq'),
    
    
    # JEF (Oct 31, 2022): this makes it sound you can just type in a project name
    # and we'll try to go to that project without putting in 'projects' or 'project'
    # For example, http://makeabilitylab.cs.uw.edu/soundwatch will go to
    # http://makeabilitylab.cs.uw.edu/project/soundwatch 
    re_path(r'(?P<project_name>[a-zA-Z ]+)/$', views.redirect_project, name='project'),
]

urlpatterns = format_suffix_patterns(urlpatterns)