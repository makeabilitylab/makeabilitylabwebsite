from django.conf.urls import url
from . import views

app_name = 'website'
urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^people/$', views.people, name='people'),
    url(r'^member/(?P<member_id>[0-9]+)/$', views.member, name='member'),
    url(r'^publications/$', views.publications, name='publications'),
    url(r'^talks/$', views.talks, name='talks'),
]