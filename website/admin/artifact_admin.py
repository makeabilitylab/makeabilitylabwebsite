from django.contrib import admin
from website.models import Artifact
from django.contrib.admin import widgets
from django.utils.html import format_html
from sortedm2m_filter_horizontal_widget.forms import SortedFilteredSelectMultiple
from website.utils.upload_validators import PDF_EXTENSIONS, RAW_FILE_EXTENSIONS
from easy_thumbnails.files import get_thumbnailer
import os
import logging

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)


def _accept_attr(extensions):
    """Build an HTML ``accept`` value (e.g. ``.pdf,.pptx``) from an extension
    allowlist. Used to seed the file inputs so both the OS file picker and the
    client-side check in ``admin_artifact_form.js`` read the allowed types
    straight from the markup — keeping them in sync with the server validators
    (issue #248)."""
    return ",".join(f".{ext}" for ext in extensions)


class ArtifactAdmin(admin.ModelAdmin):

    # Loaded on every artifact add/change form (Talk/Poster/Publication, which
    # all subclass this). Guards against losing selected files when the form is
    # submitted with a missing required field, plus drag-and-drop (issue #248).
    # PublicationAdmin defines its own Media; Django merges this base in.
    class Media:
        css = {"all": ("website/css/admin_artifact_form.css",)}
        js = ("website/js/admin_artifact_form.js",)

    # The list display lets us control what is shown in the default talk table at Home > Website > Talk
    # See: https://docs.djangoproject.com/en/dev/ref/contrib/admin/#django.contrib.admin.ModelAdmin.list_display
    list_display = ('title', 'date', 'get_first_author_last_name', 'forum_name', 'location')

    # search_fields are used for auto-complete, see:
    #   https://docs.djangoproject.com/en/3.0/ref/contrib/admin/#django.contrib.admin.ModelAdmin.autocomplete_fields
    # Includes author first/last name so artifacts are findable by who wrote them
    # (Django auto-applies DISTINCT for the M2M join). Subclasses may extend this.
    search_fields = ['title', 'forum_name', 'authors__first_name', 'authors__last_name']

    # thumbnail_preview is a computed, read-only display (see below). It must be
    # listed here so Django allows it in get_fieldsets() on the change form.
    readonly_fields = ('thumbnail_preview',)

    fieldsets = [
        (None,                      {'fields': ['title', 'authors', 'date']}),
        ('Files',                   {'fields': ['pdf_file', 'raw_file']}),
        ('Venue Info',              {'fields': ['forum_name', 'forum_url', 'location']}),
        ('Project Info',            {'fields': ['projects', 'project_umbrellas']}),
        ('Keyword Info',            {'fields': ['keywords']}),
    ]

    # Height (px) of the change-form thumbnail preview image.
    THUMBNAIL_PREVIEW_HEIGHT = 220

    def thumbnail_preview(self, obj):
        """
        Read-only image preview of the artifact's auto-generated ``thumbnail``,
        shown on the change form so editors can confirm the correct PDF is
        attached (the form otherwise only shows the "Currently: ..." filename).

        Renders an ``<img>`` (~220px tall) via easy_thumbnails — the same
        pipeline as the changelist ``get_display_thumbnail`` in TalkAdmin /
        PublicationAdmin. Degrades to a text placeholder when there is no
        thumbnail yet or the source file is missing on disk (which happens on
        the servers), rather than 500ing the whole change page.
        """
        placeholder = format_html(
            '<span style="color:#666;">Save with a PDF attached to generate a thumbnail.</span>'
        )
        if obj is None or not obj.thumbnail:
            return placeholder
        try:
            if not os.path.isfile(obj.thumbnail.path):
                return placeholder
            thumbnailer = get_thumbnailer(obj.thumbnail)
            # (0, H) constrains height to H and lets width scale with the
            # source aspect ratio (no crop — show the whole thumbnail).
            thumbnail_url = thumbnailer.get_thumbnail(
                {'size': (0, self.THUMBNAIL_PREVIEW_HEIGHT)}
            ).url
        except Exception:
            _logger.exception(
                "Could not render thumbnail preview for artifact=%s",
                getattr(obj, 'pk', None),
            )
            return placeholder
        return format_html(
            '<img src="{}" alt="PDF thumbnail" '
            'style="height:{}px; width:auto; border:1px solid #ddd;" />',
            thumbnail_url, self.THUMBNAIL_PREVIEW_HEIGHT,
        )

    # Django auto-appends the trailing colon in the admin label.
    thumbnail_preview.short_description = 'PDF thumbnail'

    def get_fieldsets(self, request, obj=None):
        """
        Inject the read-only ``thumbnail_preview`` into the 'Files' fieldset on
        the change form only. Done here (rather than in each child admin's
        ``fieldsets``) so Publication / Talk / Poster all get the preview.
        On the Add form there is no saved thumbnail yet, so it is omitted.
        """
        fieldsets = super().get_fieldsets(request, obj)
        if obj is None:
            return fieldsets
        # Build new tuples/dicts rather than mutating the class-level fieldsets
        # (ModelAdmin.get_fieldsets returns self.fieldsets by reference).
        updated = []
        for name, opts in fieldsets:
            if name == 'Files':
                fields = list(opts.get('fields', []))
                if 'thumbnail_preview' not in fields:
                    fields = fields + ['thumbnail_preview']
                opts = {**opts, 'fields': fields}
            updated.append((name, opts))
        return updated

    def get_form(self, request, obj=None, **kwargs):
        """
        Seed the ``accept`` attribute on the file inputs from the same extension
        allowlists the server validators enforce (``PDF_EXTENSIONS`` /
        ``RAW_FILE_EXTENSIONS`` in ``website.utils.upload_validators``). This gives
        the OS file picker a native type filter and is the single source of truth
        the client-side check in ``admin_artifact_form.js`` reads back from the
        DOM, so the JS can't drift from the Python rules (issue #248).

        Subclasses (Talk/Publication) call ``super().get_form()`` first and then
        layer their own widget tweaks, so this runs for all artifact admins.
        """
        form = super().get_form(request, obj, **kwargs)
        if "pdf_file" in form.base_fields:
            form.base_fields["pdf_file"].widget.attrs["accept"] = _accept_attr(PDF_EXTENSIONS)
        if "raw_file" in form.base_fields:
            form.base_fields["raw_file"].widget.attrs["accept"] = _accept_attr(RAW_FILE_EXTENSIONS)
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
        if db_field.name == "authors":
            kwargs['widget'] = SortedFilteredSelectMultiple()
        elif db_field.name == "projects":
            kwargs["widget"] = widgets.FilteredSelectMultiple("projects", is_stacked=False)
        elif db_field.name == "keywords":
            kwargs["widget"] = widgets.FilteredSelectMultiple("keywords", is_stacked=False)
        elif db_field.name == "project_umbrellas":
            kwargs["widget"] = widgets.FilteredSelectMultiple("project umbrellas", is_stacked=False)
            
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
        
        # _logger.debug(f"Started save_model with self={self}, request={request}, obj={obj}, form={form}, change={change}")
        # Removed form from debug because it can be very large
        _logger.debug(f"Started save_model with self={self}, request={request}, obj={obj}, change={change}")

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
            _logger.debug(f"Looks like we are creating a new artifact, so calling super().save_model()")
            # Call the superclass method, which calls the model.save() as well but
            # doesn't support the update_fields
            super().save_model(request, obj, form, change)