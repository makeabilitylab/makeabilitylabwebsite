from django.contrib import admin
from website.models import Artifact
from django.contrib.admin import widgets
import logging

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

class ArtifactAdmin(admin.ModelAdmin):

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """
        Overrides the formfield_for_manytomany method of the parent ModelAdmin class to customize the widgets 
        used for ManyToMany fields in the admin interface.

        Parameters:
        db_field (Field): The database field being processed.
        request (HttpRequest): The current Django HttpRequest object capturing all details of the request.
        **kwargs: Arbitrary keyword arguments.

        Returns:
        formfield (FormField): The formfield to be used in the admin interface for the ManyToMany field. The 
        widget of the formfield is customized based on the name of the db_field.
        """
        if db_field.name == "projects":
            kwargs["widget"] = widgets.FilteredSelectMultiple("projects", is_stacked=False)
        if db_field.name == "authors":
            kwargs["widget"] = widgets.FilteredSelectMultiple("authors", is_stacked=False)
        if db_field.name == "keywords":
            kwargs["widget"] = widgets.FilteredSelectMultiple("keywords", is_stacked=False)
        if db_field.name == "projects":
            kwargs["widget"] = widgets.FilteredSelectMultiple("projects", is_stacked=False)
        if db_field.name == "project_umbrellas":
            kwargs["widget"] = widgets.FilteredSelectMultiple("project umbrellas", is_stacked=False, )
            
        return super(ArtifactAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)
    
    def save_model(self, request, obj, form, change):
        """
        Overrides the save_model method of the parent ModelAdmin class. We do this
        because we want to pass the changed_fields argument to the model.save() method and
        Django does not do this by default.

        Parameters:
        request (HttpRequest): The current Django HttpRequest object capturing all details of the request.
        obj (Model): The database object being edited or created.
        form (ModelForm): The form being used to edit or create the object.
        change (bool): True if the object is being changed, False if the object is being created.

        Returns:
        None. The method saves the changes to the database.
        """
        _logger.debug(f"Started save_model with self={self}, request={request}, obj={obj}, form={form}, change={change}")

        # Get the list of changed fields
        changed_fields = form.changed_data

        # Django’s save_model method does not support updating many-to-many fields with the update_fields argument. 
        # The update_fields argument can only be used with fields that are stored directly on the model, not those 
        # that are stored through a separate table, such as many-to-many fields.
        # So, we need to exclude m2m fields
        m2m_fields = {field.name for field in obj._meta.many_to_many}
        changed_fields = [field for field in changed_fields if field not in m2m_fields]

        # If this is not the first time we are saving this model (i.e., we are making a change)
        # Then save the object with the update_fields argument
        if obj.pk is not None:
            _logger.debug(f"Looks like we are modifying artifact={obj.id} with changed_fields={changed_fields}")
            obj.save(update_fields=changed_fields)
        else:
            # Call the superclass method, which calls the model.save() as well but
            # doesn't support the update_fields
            super().save_model(request, obj, form, change)