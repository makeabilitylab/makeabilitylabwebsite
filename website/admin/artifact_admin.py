from django.contrib import admin
from website.models import Artifact
import logging

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

class ArtifactAdmin(admin.ModelAdmin):
    
    def save_model(self, request, obj, form, change):
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