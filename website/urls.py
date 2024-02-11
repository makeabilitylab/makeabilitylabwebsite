from django.urls import path, re_path
from django.views.generic.base import RedirectView
from . import views
from rest_framework.urlpatterns import format_suffix_patterns

# Need to import admin because we now have "lazy" loading where
# we try to go to a project page if someone puts http://makeabilitylab.cs.uw.edu/soundwatch
# then website will try to load http://makeabilitylab.cs.uw.edu/project/soundwatch 
from django.contrib import admin

# You need to define an app_name in urls.py
# See: https://docs.djangoproject.com/en/dev/topics/http/urls/#url-namespaces-and-included-urlconfs
app_name = "website"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('people/', views.people, name='people'),
    path('member/<int:member_id>/', views.member, name='member'),
    path('member/<slug:member_id>/', views.member, name='member'),
    path('publications/', views.publications, name='publications'),
    path('talks/', views.talks, name='talks'),
    path('videos/', views.videos, name='videos'),
    path('projects/', views.project_listing, name='projects'),
    path('projects/<slug:project_name>/', views.project, name='project'),
    path('project/<slug:project_name>/', views.project, name='project'),
    path('news/', views.news_listing, name='news_listing'),
    path('view-project-people/', views.view_project_people, name='view_project_people'),
    path('ajax_example/', views.ajax_example, name='ajax_example'),

    # First try to match on the news id (for historical compatibility) then match on the slug
    path('news/<int:id>/', views.news_item, name='news_item_by_id'),
    path('news/<slug:slug>/', views.news_item, name='news_item_by_slug'),
    path('faq/', views.faq, name='faq'),

    # Redirect any URL not already matched to the project view
    # JEF (Oct 31, 2022): this makes it sound you can just type in a project name
    # and we'll try to go to that project without putting in 'projects' or 'project'
    # For example, http://makeabilitylab.cs.uw.edu/soundwatch will go to
    # http://makeabilitylab.cs.uw.edu/project/soundwatch 
    path('<slug:project_name>/', RedirectView.as_view(url='/project/%(project_name)s/'), name='redirect_project'),
]

# The format_suffix_patterns function from Django REST Framework adds optional format 
# suffixes to your URLs, allowing clients to specify the data format (like .json or .api) 
# directly in the URL.
#
# This function modifies your URL patterns to include an optional format parameter, which is 
# passed to your views.
# See: https://www.django-rest-framework.org/api-guide/format-suffixes/#format_suffix_patterns
urlpatterns = format_suffix_patterns(urlpatterns)