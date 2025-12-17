# from django.contrib import admin
# from .artifact_admin import ArtifactAdmin
# from . import banner_admin, news_admin, person_admin, photo_admin, poster_admin,\
#     project_admin, project_umbrella_admin, publication_admin, talk_admin, video_admin,\
#         keyword_admin, grant_admin, sponsor_admin, position_admin
# from website.models import Keyword, Sponsor
# import django # so we can print out the Django version in the admin interface
# from django.conf import settings # so we can print out the Makeability Lab website version in the admin interface

# # If you want a model to showup in the admin interface, you have two options:
# # 1. Register the model with admin.site.register(ModelName)
# # 2. Create a ModelAdmin class and register that with admin.site.register(ModelName, ModelAdminName) or
# #    if you’re using the @admin.register decorator in your individual model_admin.py files, you don’t need to 
# #    use admin.site.register() in your __init__.py. The decorator takes care of registering the models.

# # For modifying more on the front admin landing page, see https://medium.com/django-musings/customizing-the-django-admin-site-b82c7d325510
# # admin.site.index_title = f"Makeability Lab Admin. Django version: {django.get_version()} \
# #     Makeability Lab Website Version: {settings.ML_WEBSITE_VERSION} | DEBUG MODE={settings.DEBUG}\
# #     INTERNAL_IPS={settings.INTERNAL_IPS}"

# admin.site.site_header = f"Makeability Lab Website v{settings.ML_WEBSITE_VERSION}"  # Top of every page
# admin.site.site_title = "Makeability Lab Admin"   # Browser tab title
# admin.site.index_title = "Makeability Lab Admin Dashboard"        # Title on the index page only

"""
Makeability Lab Admin Configuration

This module configures the Django admin interface for the Makeability Lab website.
It uses a custom AdminSite (defined in sites.py) that reorganizes models into
workflow-based groupings rather than Django's default app-based organization.

The custom organization prioritizes:
1. Artifacts (Publications, Talks, Posters, Videos) - most common tasks
2. Projects & Media - project-related content
3. Grants & Funding - funding management
4. People - lab member management  
5. Configuration - rarely-changed settings
6. Administration - Django auth (least used)
"""

from django.contrib import admin

# Import the custom admin site
from website.admin.admin_site import ml_admin_site

# Replace the default admin site with our custom one
admin.site = ml_admin_site

# Import the base ArtifactAdmin for use by other admin classes
from .artifact_admin import ArtifactAdmin

# Import all admin modules to trigger their @admin.register decorators
# The decorators will register models with our custom admin.site
from . import (
    banner_admin,
    grant_admin,
    keyword_admin,
    news_admin,
    person_admin,
    photo_admin,
    position_admin,
    poster_admin,
    project_admin,
    project_umbrella_admin,
    publication_admin,
    sponsor_admin,
    talk_admin,
    video_admin,
)