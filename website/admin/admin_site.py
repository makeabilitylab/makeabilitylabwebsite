"""
Custom Django AdminSite for the Makeability Lab website.

This module provides a customized admin interface with:
- Reorganized model groupings optimized for common workflows
- Custom section ordering (most-used sections at top)
- Help text for guiding new users

The goal is to make the admin interface intuitive for lab members,
particularly students who primarily add publications and related artifacts.

Usage:
    In settings.py INSTALLED_APPS, replace:
        'django.contrib.admin'
    with:
        'website.admin.admin_site.MakeabilityLabAdminConfig'
    
    This ensures admin.site points to our custom site before any
    @admin.register decorators run, so all existing admin files work
    without modification.
"""

from django.contrib import admin
from django.contrib.admin.apps import AdminConfig
from django.conf import settings
from django.contrib.auth.models import Group, User     
from django.contrib.auth.admin import GroupAdmin, UserAdmin 


class MakeabilityLabAdminSite(admin.AdminSite):
    """
    Custom admin site with Makeability Lab branding and organization.
    
    Reorganizes the default Django admin index page to group models
    by workflow rather than by Django app, making it easier for lab
    members to find what they need.
    """
    
    site_header = f"Makeability Lab Website v{settings.ML_WEBSITE_VERSION}"
    site_title = "Makeability Lab Admin"
    index_title = "Makeability Lab Admin Dashboard"
    
    # Define custom groupings with display order
    # Each group: (group_name, [model_names], help_text or None)
    CUSTOM_GROUPS = [
        (
            "Artifacts",
            ["Publication", "Talk", "Poster", "Video"],
            "Tip: When adding a talk, poster, or video, start from the related "
            "Publication's edit page—common fields like title, authors, date, and "
            "venue will auto-fill, saving time and reducing errors."
        ),
        (
            "People & News",
            ["Person", "News"],
            "Please keep your ugrads up-to-date! Make sure you add them to your projects, set their mentorship info, and keep dates accurate."
        ),
        (
            "Projects & Media", 
            ["Project", "Banner", "Photo"],
            None
        ),
        (
            "Grants & Funding",
            ["Grant", "Sponsor"],
            "Generally, Jon will handle these. Please contact him if you think you need to edit."
        ),
        (
            "Configuration",
            ["Keyword", "ProjectUmbrella"],
            "These are used to tag and organize content across the site. You will not typically modify keywords directly; instead, you'll add them when editing Publications, Projects, etc."
        ),
        (
            "Administration",
            ["Group", "User"],
            None
        ),
    ]
    
    def get_app_list(self, request, app_label=None):
        """
        Return a reorganized list of apps/models for the admin index.
        
        Instead of Django's default organization by app, this groups models
        by workflow/purpose to match how lab members actually use the admin.
        
        Args:
            request: The current HttpRequest.
            app_label: Optional app label to filter by (used in app index views).
            
        Returns:
            list: Reorganized app list with custom groupings.
        """
        # Get the default app list from Django
        original_app_list = super().get_app_list(request, app_label)
        
        # If we're on a specific app's page, use default behavior
        if app_label:
            return original_app_list
        
        # Build a lookup dict: model_name -> model_dict
        model_lookup = {}
        for app in original_app_list:
            for model in app.get('models', []):
                # Use the model's object_name (e.g., "Publication", "Person")
                model_name = model.get('object_name')
                if model_name:
                    model_lookup[model_name] = model
        
        # Build the custom grouped list
        custom_app_list = []
        used_models = set()  # Track which models we've placed in groups
        
        for group_name, model_names, help_text in self.CUSTOM_GROUPS:
            models = []
            for name in model_names:
                if name in model_lookup:
                    models.append(model_lookup[name])
                    used_models.add(name)
            
            # Only add the group if it has models the user can access
            if models:
                custom_app_list.append({
                    'name': group_name,
                    'app_label': group_name.lower().replace(' & ', '_').replace(' ', '_'),
                    'app_url': None,  # No app-level URL for custom groups
                    'has_module_perms': True,
                    'models': models,
                    'help_text': help_text,  # Custom field for our template
                })
        
        # Collect any models not in our custom groups (so nothing gets lost)
        # This ensures new models added later still appear even if we forget
        # to add them to CUSTOM_GROUPS
        ungrouped_models = []
        for app in original_app_list:
            for model in app.get('models', []):
                model_name = model.get('object_name')
                if model_name and model_name not in used_models:
                    ungrouped_models.append(model)
        
        # If there are ungrouped models, add them in an "Other" section
        if ungrouped_models:
            custom_app_list.append({
                'name': 'Other',
                'app_label': 'other',
                'app_url': None,
                'has_module_perms': True,
                'models': ungrouped_models,
                'help_text': "Models not yet assigned to a category. Please update "
                             "CUSTOM_GROUPS in admin_site.py to organize these.",
            })
        
        return custom_app_list


# Create the custom admin site instance
ml_admin_site = MakeabilityLabAdminSite(name='admin')

# Ensure standard auth models are registered with our custom site
if not ml_admin_site.is_registered(Group):
    ml_admin_site.register(Group, GroupAdmin)

if not ml_admin_site.is_registered(User):
    ml_admin_site.register(User, UserAdmin)