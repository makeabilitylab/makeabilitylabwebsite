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

app_name = "website"
urlpatterns = [
    # Matches the URL starting with "admin/" and routes it to the Django admin site.
    # re_path(r"^admin/", admin.site.urls),

    # Matches the root URL (i.e., the homepage) and routes it to the `index` view.
    re_path(r'^$', views.index, name='index'),

    # Matches the URL "people/" and routes it to the `people` view.
    re_path(r'^people/$', views.people, name='people'),

    # Matches URLs like "member/123/" where 123 is a numeric member ID, and routes it 
    # to the `member` view.
    # re_path(r'^member/(?P<member_id>[0-9]+)/$', views.member, name='member'),
    path('member/<int:member_id>/', views.member, name='member_by_id'),

    # Matches URLs like "member/john-doe/" where "john-doe" is a member ID consisting of 
    # lowercase letters and hyphens, and routes it to the `member` view.
    # re_path(r'^member/(?P<member_id>[-a-z]+)/$', views.member, name='member'),
    path('member/<str:member_name>/', views.member, name='member_by_name'),

    # Matches the URL "publications/" and routes it to the `publications` view.
    re_path(r'^publications/$', views.publications, name='publications'),

    # Matches the URL "talks/" and routes it to the `talks` view.
    re_path(r'^talks/$', views.talks, name='talks'),

    # Matches the URL "videos/" and routes it to the `videos` view.
    re_path(r'^videos/$', views.videos, name='videos'),

    # Matches the URL "projects/" and routes it to the `project_listing` view.
    re_path(r'^projects/$', views.project_listing, name='projects'),

    # Matches URLs like "projects/project-name/" where "project-name" consists of letters, hyphens, 
    # and spaces, and routes it to the `project` view.
    re_path(r'^projects/(?P<project_name>[a-zA-Z\- ]+)/$', views.project, name='project'),

    # Matches URLs like "project/project-name/" where "project-name" consists of letters, hyphens, 
    # and spaces, and routes it to the `project` view.
    re_path(r'^project/(?P<project_name>[a-zA-Z\- ]+)/$', views.project, name='project'),

    # Matches the URL "news/" and routes it to the `news_listing` view.
    re_path(r'^news/$', views.news_listing, name='news_listing'),

    # Matches the URL "view-project-people/" and routes it to the `view_project_people` view.
    path('view-project-people/', views.view_project_people, name='view_project_people'),

    # Matches URLs like "media/publications/filename.pdf" where "filename.pdf" can be any string, 
    # and routes it to the `serve_pdf` view. 
    # serve_pdf uses fuzzy matching to find the closest matching filename (within a threshold)
    # Match files directly in the "publications" path
    # re_path(r'^media/publications/(?P<filename>[^/]+)$', views.serve_pdf, name='serve_pdf'),
    re_path(r'^media/publications/([^/]+)$', views.serve_pdf, name='serve_pdf'),
    # re_path(r'^media/publications/(?P<filename>.+)$', views.serve_pdf, name='serve_pdf'),
    # path('media/publications/<path:filename>', views.serve_pdf, name='serve_pdf'),

    # Matches URLs like "news/123/" where 123 is a numeric news ID, and routes it to the `news_item` view.
    path('news/<int:id>/', views.news_item, name='news_item_by_id'),

    # Matches URLs like "news/some-slug/" where "some-slug" is a slug, and routes it to the `news_item` view.
    path('news/<slug:slug>/', views.news_item, name='news_item_by_slug'),

    # Matches the URL "faq/" and routes it to the `faq` view.
    re_path(r'^faq/$', views.faq, name='faq'),

    # Matches URLs like "project-name/" where "project-name" consists of letters, hyphens, and spaces, 
    # and routes it to the `redirect_project` view.
    # This is a catch-all pattern that should be placed at the end to avoid catching other patterns.
    # For example, http://makeabilitylab.cs.uw.edu/soundwatch will go to
    # http://makeabilitylab.cs.uw.edu/project/soundwatch 
    # re_path(r'(?P<project_name>[a-zA-Z\- ]+)/$', views.redirect_project, name='project'),
]

urlpatterns = format_suffix_patterns(urlpatterns)