from django.conf.urls import url
from . import views

app_name = 'website'
urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^people/$', views.people, name='people'),
    url(r'^member/(?P<member_id>[0-9]+)/$', views.member, name='member'),
    url(r'^publications/$', views.publications, name='publications'),
    url(r'^publications/(?P<filter>[\w -]{0,50})/$', views.publications, name='publications'),
    url(r'^talks/$', views.talks, name='talks'),
    url(r'^talks/(?P<filter>[\w -]{0,50})/$', views.talks, name='talks'),
    url(r'^projects/$', views.projects, name='projects'),
    url(r'^projects/(?P<filter>[\w -]{0,50})/$', views.projects, name='projects'),
    url(r'^project/(?P<project_name>[a-zA-Z ]+)/$', views.project_ind, name='project_ind'),
    url(r'^news/(?P<news_id>[0-9]+)/$', views.news, name='news')
]
