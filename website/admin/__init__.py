from django.contrib import admin
from .artifact_admin import ArtifactAdmin
from . import banner_admin, news_admin, person_admin, photo_admin, poster_admin,\
    project_admin, project_umbrella_admin, publication_admin, talk_admin, video_admin,\
        keyword_admin, grant_admin
from website.models import Keyword, Sponsor
import django # so we can print out the Django version in the admin interface
from django.conf import settings # so we can print out the Makeability Lab website version in the admin interface

# If you want a model to showup in the admin interface, you have two options:
# 1. Register the model with admin.site.register(ModelName)
# 2. Create a ModelAdmin class and register that with admin.site.register(ModelName, ModelAdminName) or
#    if you’re using the @admin.register decorator in your individual model_admin.py files, you don’t need to 
#    use admin.site.register() in your __init__.py. The decorator takes care of registering the models.
admin.site.register(Sponsor)

# For modifying more on the front admin landing page, see https://medium.com/django-musings/customizing-the-django-admin-site-b82c7d325510
admin.site.index_title = f"Makeability Lab Admin. Django version: {django.get_version()} \
    Makeability Lab Website Version: {settings.ML_WEBSITE_VERSION} | DEBUG MODE={settings.DEBUG}\
    INTERNAL_IPS={settings.INTERNAL_IPS}"
