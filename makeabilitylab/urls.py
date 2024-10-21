# JEF Note (10/21/2024)
# I'm writing this note because urls.py is confusing. There are multiple urls.py: one in the root directory 
# and one for each app. This file is the top-level urls.py file in the root directory.
#
# 1. The top-level urls.py is the one that Django uses to route URLs to the correct app.
#    This file is the top-level urls.py file! It's located in the root directory of 
#    the Django project and includes URL patterns for the entire project and often routes 
#    requests to the appropriate app-level urls.py file. Notice how its urlpatterns includes
#    include('website.urls') which routes requests to the website app. Note custom 404 routing 
#    and other error handling must be handled in the root urls.py, which is in makeabilitylab/urls.py
#
# 2. Then we also have app-level urls.py files. These files are located in each app directory.
#    Currently, this Django project only has one app: the website app. The app-level urls.py file
#    is in website/urls.py
# 

from django.urls import include, re_path, path
from django.contrib import admin
from django.conf.urls.static import static
from django.views.static import serve
from django.conf import settings
from django.conf.urls import handler404

# The default page_not_found() view is overridden by handler404
# https://docs.djangoproject.com/en/5.1/topics/http/views/#customizing-error-views
handler404 = "website.views.custom_404"

urlpatterns = [
    #Info on how to route root to website was found here http://stackoverflow.com/questions/7580220/django-urls-howto-map-root-to-app
    re_path(r'', include('website.urls')),
    re_path(r'^admin/', admin.site.urls),
    re_path(r'^ckeditor/', include('ckeditor_uploader.urls')),
    path("__debug__/", include("debug_toolbar.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# serving media files only in debug mode
if settings.DEBUG:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {
            'document_root': settings.MEDIA_ROOT
        }),
    ]