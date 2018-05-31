from django.conf.urls import url
from . import views

app_name = 'website'
urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^people/$', views.people, name='people'),
    url(r'^member/(?P<member_id>[0-9]+)/$', views.member, name='member'),
    # url(r'^member/(?P<member_id>[-a-z]+)/$', views.member, name='member'),
    url(r'^publications/$', views.publications, name='publications'),
    url(r'^talks/$', views.talks, name='talks'),
    url(r'^videos/$', views.videos, name='videos'),
    url(r'^projects/$', views.projects, name='projects'),
    url(r'^projects/(?P<project_name>[a-zA-Z ]+)/$', views.project, name='project'),
    url(r'^project/(?P<project_name>[a-zA-Z ]+)/$', views.project, name='project'),
    url(r'^news/(?P<news_id>[0-9]+)/$', views.news, name='news')
]
