from django import forms
from django.contrib import admin
from django.core.files import File
from website.models import Position, Person, ProjectRole, Publication, Talk
from website.models.position import Title
from website.models.person import PERSON_THUMBNAIL_SIZE
from easy_thumbnails.exceptions import InvalidImageFormatError # for handling invalid images
from website.admin_list_filters import PositionRoleListFilter, PositionTitleListFilter
from website.admin.utils import (get_active_professors_queryset, get_active_mentors_queryset,
                                 related_count_subquery)
from image_cropping import ImageCroppingMixin
from image_cropping.widgets import EasterEggCropImageWidget
import website.utils.fileutils as ml_fileutils

from django.utils.html import format_html # for formatting thumbnails
from easy_thumbnails.files import get_thumbnailer # for generating thumbnails
import os # for checking if thumbnail file exists
from website.utils import timeutils
from website.admin.admin_site import ml_admin_site

import logging
_logger = logging.getLogger(__name__)


class PersonAdminForm(forms.ModelForm):
    """Person admin form that lets editors pick a default easter-egg figure.

    The Star Wars easter-egg picker (#1304) writes the chosen figure's basename
    into the hidden ``easter_egg_starwars_choice`` field. On save, when the
    editor shuffled to a figure and didn't also upload their own image, we copy
    that chosen figure into ``Person.easter_egg`` so the previewed image (and its
    crop box) is exactly what persists. This applies whether the field was empty
    (new Person) or already had an image (an editor swapping their easter egg) —
    the field is only populated by an explicit shuffle, so an untouched edit
    keeps the existing image, and an empty-and-untouched field still falls
    through to ``Person.save()``'s random pick (the non-admin/bulk path).

    The choice is validated against :func:`fileutils.list_starwars_images`, so a
    crafted value can't read an arbitrary file off disk.
    """

    # Not a model field: a browser-set hint for which Star Wars figure to use.
    easter_egg_starwars_choice = forms.CharField(
        required=False, widget=forms.HiddenInput
    )

    class Meta:
        model = Person
        fields = "__all__"

    def clean_easter_egg_starwars_choice(self):
        """Reject anything that isn't a known Star Wars figure basename."""
        choice = (self.cleaned_data.get("easter_egg_starwars_choice") or "").strip()
        if not choice:
            return ""
        # os.path.basename guards against path components; the membership check
        # is the real gate (only figures we actually ship are accepted).
        if os.path.basename(choice) != choice or choice not in ml_fileutils.list_starwars_images():
            raise forms.ValidationError("Unknown Star Wars figure.")
        return choice

    def save(self, commit=True):
        person = super().save(commit=False)

        # Copy the chosen figure into easter_egg when the editor shuffled to one
        # and didn't also upload their own image (upload always wins). The choice
        # field is only set by an explicit shuffle, so this both seeds a new
        # Person's default and lets an existing one swap figures; an untouched
        # field leaves easter_egg alone. self.files holds uploads.
        choice = self.cleaned_data.get("easter_egg_starwars_choice")
        uploaded = self.files.get(self.add_prefix("easter_egg"))
        if choice and not uploaded:
            src_path = os.path.join(ml_fileutils.get_starwars_image_dir(), choice)
            # Person.save() reads the file during super().save(), so keep the
            # handle open until after the model is saved (mirrors the random
            # fallback pattern in Person.save()).
            fh = open(src_path, "rb")
            self._easter_egg_fh = fh
            person.easter_egg = File(fh, name=choice)

        if commit:
            person.save()
            self.save_m2m()
            self._close_easter_egg_fh()
        return person

    def _close_easter_egg_fh(self):
        fh = getattr(self, "_easter_egg_fh", None)
        if fh is not None:
            fh.close()
            self._easter_egg_fh = None

class PositionInline(admin.StackedInline):

    # This line specifies that the inline model is the Position model.
    # This means that the Position records will be edited inline on the Person model's admin page.
    model = Position

    # This line specifies the name of the ForeignKey field in the Position model 
    # that links to the parent model (Person). This is necessary because the Position model 
    # has multiple ForeignKey fields linking to the Person model (person, advisor, co_advisor, 
    # grad_mentor). By setting fk_name to "person", we're specifying that the inline positions 
    # are linked to the main owner of the position (the "person" field), not any of the other roles.
    fk_name = "person"

    # This line specifies the number of empty forms to display for the inline model.
    # By setting extra to 0, we're specifying that no extra empty forms will be displayed by default.
    # The user can still add new positions by clicking on the "Add another Position" link.
    extra = 0 

    fieldsets = [
        (None,                      {'fields': ['start_date', 'end_date']}),
        ('Role and Affiliations',   {'fields': ['role', 'title', 'department', 'school']}),
        ('Advisors/Mentors',        {'fields': ['advisor', 'co_advisor', 'grad_mentor']}),
    ]

    autocomplete_fields = ['co_advisor', 'grad_mentor']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Customize foreign key dropdowns for advisor and mentor fields.
        
        Filters the queryset to show only active professors for advisor/co_advisor
        fields, and active senior lab members for the grad_mentor field.
        """
        if db_field.name in ("advisor", "co_advisor"):
            kwargs["queryset"] = get_active_professors_queryset()
        elif db_field.name == "grad_mentor":
            kwargs["queryset"] = get_active_mentors_queryset()

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

class ProjectRoleInline(admin.StackedInline):
    model = ProjectRole
    extra = 0
    autocomplete_fields = ['project']


@admin.register(Person, site=ml_admin_site)
class PersonAdmin(ImageCroppingMixin, admin.ModelAdmin):
    form = PersonAdminForm

    fieldsets = [
        (None,                      {'fields': ['first_name', 'middle_name', 'last_name', 'image', 'cropping', 'easter_egg', 'easter_egg_crop', 'easter_egg_starwars_choice']}),
        ('Bio',                     {'fields': ['bio', 'personal_website', 'github']}),
        ('Socials',                 {'fields': ['twitter', 'bluesky', 'threads', 'mastodon', 'linkedin', 'google_scholar', 'orcid']}),
        ('For Alumni (Next Position)', {'fields': ['next_position', 'next_position_url']}),
    ]

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        """Give easter_egg the Star Wars picker widget (preview/shuffle, #1304).

        The headshot ``image`` field keeps the plain crop widget — only the
        easter egg gets a default-on-load figure the editor can shuffle.
        """
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == 'easter_egg' and formfield is not None:
            widget = EasterEggCropImageWidget()
            widget.starwars_images = [
                {'name': name, 'url': ml_fileutils.get_starwars_image_url(name)}
                for name in ml_fileutils.list_starwars_images()
            ]
            formfield.widget = widget
        return formfield

    def save_model(self, request, obj, form, change):
        """Persist, then release the easter-egg figure file handle (if any)."""
        super().save_model(request, obj, form, change)
        if hasattr(form, '_close_easter_egg_fh'):
            form._close_easter_egg_fh()

    exclude = ('bio_datetime_modified',) # don't show this field as it's auto-calculated

    # inlines allow us to edit models on the same page as a parent model
    # see: https://docs.djangoproject.com/en/1.11/ref/contrib/admin/#inlinemodeladmin-objects
    inlines = [PositionInline, ProjectRoleInline]

    # We must define search_fields in order to use the autocomplete_fields option.
    # url_name is included so the Data Health "url_name collisions" check can deep-link
    # here with ?q=<url_name> to surface the colliding rows.
    search_fields = ['first_name', 'last_name', 'url_name',]

    def get_search_results(self, request, queryset, search_term):
        """Role-filter the admin autocomplete results for advisor/mentor fields (#1126).

        ``PositionInline.formfield_for_foreignkey`` filters the plain ``advisor``
        <select>, but ``co_advisor`` and ``grad_mentor`` are ``autocomplete_fields``:
        their options come from this endpoint (``AutocompleteJsonView``), which
        bypasses ``formfield_for_foreignkey``. Without this, the autocomplete search
        would offer every person (e.g. undergrads as co-advisors). We narrow the
        queryset to the same role-appropriate sets used for the plain dropdowns,
        keyed off the requesting Position field passed by the autocomplete view.
        """
        queryset, may_have_duplicates = super().get_search_results(
            request, queryset, search_term)

        if request.GET.get('model_name') == 'position':
            field_name = request.GET.get('field_name')
            if field_name in ('advisor', 'co_advisor'):
                allowed = get_active_professors_queryset()
            elif field_name == 'grad_mentor':
                allowed = get_active_mentors_queryset()
            else:
                allowed = None

            if allowed is not None:
                queryset = queryset.filter(
                    pk__in=allowed.values_list('pk', flat=True))

        return queryset, may_have_duplicates

    # The list display lets us control what is shown in the default persons table at Home > Website > People
    # info on displaying multiple entries comes from http://stackoverflow.com/questions/9164610/custom-columns-using-django-admin
    # The count columns (project_count / pub_count / talk_count) read annotations
    # set in get_queryset() rather than the per-row model count methods (#1346).
    list_display = ('get_full_name', 'get_display_thumbnail', 'get_current_title', 'get_current_role', 'is_active',
                    'get_start_date', 'get_cur_pos_start_date', 'get_end_date', 'recent_projects', 'project_count', 'pub_count',
                    'talk_count', 'display_time_current_position', 'display_total_time_as_member')

    list_filter = (PositionRoleListFilter, PositionTitleListFilter)

    # The changelist renders ~14 columns of position/count data per person; cap
    # the page so the per-row thumbnail filesystem check stays bounded (#1346).
    list_per_page = 50

    def get_queryset(self, request):
        """Make the People changelist issue a roughly constant number of queries
        regardless of how many people are listed (the #1346 perf audit).

        - ``position_set`` is prefetched because nearly every column ("current
          title/role", dates, durations, is_active) and the Role filter funnel
          through ``Person.get_latest_position``, which now reads this prefetch
          cache instead of issuing ``.latest()`` per row.
        - ``projectrole_set__project`` backs :meth:`recent_projects`.
        - the three ``_*_count`` annotations back the sortable count columns,
          replacing three per-row ``COUNT(*)`` queries with scalar subqueries.
        """
        return (super().get_queryset(request)
                .prefetch_related('position_set', 'projectrole_set__project')
                .annotate(
                    _project_count=related_count_subquery(ProjectRole, 'person'),
                    _pub_count=related_count_subquery(Publication, 'authors'),
                    _talk_count=related_count_subquery(Talk, 'authors'),
                ))

    def recent_projects(self, obj):
        """The person's three most recent project roles (by start_date), as a
        comma-separated list of project names. Reads ``obj.projectrole_set.all()``
        (prefetched with its ``project`` in :meth:`get_queryset`) and sorts in
        Python, so it adds no per-row queries on the changelist."""
        roles = sorted(obj.projectrole_set.all(),
                       key=lambda role: role.start_date, reverse=True)[:3]
        return ', '.join(str(role.project) for role in roles)

    recent_projects.short_description = 'Recent Projects'  # Sets column name in admin interface

    def project_count(self, obj):
        """Number of project roles (annotated in get_queryset; sortable)."""
        return obj._project_count
    project_count.short_description = 'Projects'
    project_count.admin_order_field = '_project_count'

    def pub_count(self, obj):
        """Number of publications authored (annotated in get_queryset; sortable)."""
        return obj._pub_count
    pub_count.short_description = 'Pubs'
    pub_count.admin_order_field = '_pub_count'

    def talk_count(self, obj):
        """Number of talks given (annotated in get_queryset; sortable)."""
        return obj._talk_count
    talk_count.short_description = 'Talks'
    talk_count.admin_order_field = '_talk_count'

    def display_time_current_position(self, obj):
        """Displays the time in the current position"""
        duration = obj.get_time_in_current_position

        if duration:
            return timeutils.humanize_duration(duration, sig_figs=2, use_abbreviated_units=True)
        else:
            return 'N/A'
    
    display_time_current_position.short_description = 'Time in Current Position'
    
    def display_total_time_as_member(self, obj):
        """Displays the total time as a member of the lab"""
        duration = obj.get_total_time_as_member
        
        if duration:
            return timeutils.humanize_duration(duration, sig_figs=2, use_abbreviated_units=True)
        else:
            return 'N/A'
    
    display_total_time_as_member.short_description = 'Total Time as Member'

    def get_display_thumbnail(self, obj):
        if obj.image and os.path.isfile(obj.image.path):
            # Use easy_thumbnails to generate a thumbnail
            thumbnailer = get_thumbnailer(obj.image)
            thumbnail_options = {'size': (PERSON_THUMBNAIL_SIZE[0], PERSON_THUMBNAIL_SIZE[1]), 'crop': True}
            
            try:
                thumbnail_url = thumbnailer.get_thumbnail(thumbnail_options).url
                return format_html('<img src="{}" height="50" style="border-radius: 50%;"/>', thumbnail_url)
            except InvalidImageFormatError as e:
                _logger.error(f"When trying to generate a thumbnail for {obj.get_full_name()}, received a invalid image format error: {e}")
            except PermissionError as e:
                _logger.error(f"When trying to generate a thumbnail for {obj.get_full_name()}, received permission error: {e}")

        return 'No Thumbnail'
    
    get_display_thumbnail.short_description = 'Thumbnail'


