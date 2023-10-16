"""makeabilitylab URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Import the include() function: from django.conf.urls import url, include
    3. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""

# Django 4+ eliminated django.conf.urls import url
# See: https://stackoverflow.com/a/70319607
# from django.conf.urls import include, url

from django.urls import include, re_path, path
from django.contrib import admin
from django.conf.urls.static import static
from django.views.static import serve
from django.conf import settings

urlpatterns = [
    #Info on how to route root to website was found here http://stackoverflow.com/questions/7580220/django-urls-howto-map-root-to-app
    re_path(r'', include('website.urls')),
    re_path(r'^admin/', admin.site.urls),
    re_path(r'^ckeditor/', include('ckeditor_uploader.urls')),
    # path("select2/", include("django_select2.urls")), I experimented with select2 and I was not that impressed
    path("__debug__/", include("debug_toolbar.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# serving media files only on debug mode
if settings.DEBUG:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {
            'document_root': settings.MEDIA_ROOT
        }),
    ]