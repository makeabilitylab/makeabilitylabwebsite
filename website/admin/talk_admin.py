from django.contrib import admin
from django.contrib.admin import widgets
from website.models import Talk
import logging

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

@admin.register(Talk)
class TalkAdmin(admin.ModelAdmin):
    # The list display lets us control what is shown in the default talk table at Home > Website > Talk
    # See: https://docs.djangoproject.com/en/dev/ref/contrib/admin/#django.contrib.admin.ModelAdmin.list_display
    list_display = ('title', 'date', 'get_speakers_as_csv', 'forum_name', 'location', 'talk_type')

    # search_fields are used for auto-complete, see:
    #   https://docs.djangoproject.com/en/3.0/ref/contrib/admin/#django.contrib.admin.ModelAdmin.autocomplete_fields
    search_fields = ['title', 'forum_name']

    autocomplete_fields = ['video']

    # fieldsets control how the "add/change" admin views look
    fieldsets = [
        (None,                      {'fields': ['title', 'authors', 'date']}),
        ('Files',                   {'fields': ['pdf_file', 'raw_file']}),
        ('Talk Venue Info',         {'fields': ['talk_type', 'forum_name', 'forum_url', 'location']}),
        ('Links',                   {'fields': ['video', 'slideshare_url']}),
        ('Project Info',            {'fields': ['projects', 'project_umbrellas']}),
        ('Keyword Info',            {'fields': ['keywords']}),
    ]

    def get_form(self, request, obj=None, **kwargs):
        """
        Overrides the get_form method of the parent ModelAdmin class to customize the form used in the admin interface.

        Parameters:
        request (HttpRequest): The current Django HttpRequest object capturing all details of the request.
        obj (Model, optional): The database object being edited. Default is None, which means this is a new object.
        **kwargs: Arbitrary keyword arguments.

        Returns:
        form (ModelForm): The form to be used in the admin interface. The 'authors' field label is changed to 'Speakers'.
        """
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['authors'].label = 'Speakers'
        return form
    
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
         
        # print("TalkAdmin.formfield_for_manytomany: db_field: {} db_field.name {} request: {}".format(db_field, db_field.name, request))
        if db_field.name == "projects":
            kwargs["widget"] = widgets.FilteredSelectMultiple("projects", is_stacked=False)
        if db_field.name == "project_umbrellas":
            kwargs["widget"] = widgets.FilteredSelectMultiple("project umbrellas", is_stacked=False, )
        if db_field.name == "authors":
            # Uncomment the following block of code to limit the speakers field in the admin UI only to current lab members
            # Note: we don't actually want to do this (see https://github.com/jonfroehlich/makeabilitylabwebsite/issues/534)
            # but keeping it here because code may be useful in the future for other areas of admin interface
            # current_member_and_collab_ids = [person.id for person in Person.objects.all() if person.is_current_member()]
            # filtered_speakers = Person.objects.filter(id__in=current_member_and_collab_ids).order_by('first_name')
            # kwargs["queryset"] = filtered_speakers
            kwargs["widget"] = widgets.FilteredSelectMultiple("authors", is_stacked=False)
        if db_field.name == "keywords":
            kwargs["widget"] = widgets.FilteredSelectMultiple("keywords", is_stacked=False)
        
        return super(TalkAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)
    
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
            _logger.debug(f"Looks like we are modifying talk={obj.id} with changed_fields={changed_fields}")
            obj.save(update_fields=changed_fields)
        else:
            # Call the superclass method, which calls the model.save() as well but
            # doesn't support the update_fields
            super().save_model(request, obj, form, change)