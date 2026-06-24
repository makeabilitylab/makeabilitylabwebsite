from django.contrib import admin
from django.contrib.admin import widgets
from website.models import (Project, ProjectAlias, Banner, Photo, ProjectRole, Grant,
                            Publication, Talk, Video, Person)
from website.models.project import PROJECT_THUMBNAIL_SIZE
from website.admin_list_filters import ActiveProjectsFilter
from image_cropping import ImageCroppingMixin

from django.utils.html import format_html # for formatting thumbnails
from easy_thumbnails.files import get_thumbnailer # for generating thumbnails
import os # for checking if thumbnail file exists
from django import forms
from django.db.models import F, Q, Count, OuterRef, Subquery, IntegerField, Value
from django.db.models.functions import Greatest, Coalesce
from website.admin.utils import related_count_subquery
from website.admin.admin_site import ml_admin_site


def _contributor_count_subquery():
    """Distinct count of people who either hold a ProjectRole on the project OR
    are an author on one of its publications — matching Project.get_contributors,
    which unions those two sets (#1346). One correlated subquery: count distinct
    Person ids matching either relation for the outer project, grouped by a
    constant so it returns a single scalar."""
    people = (Person.objects
              .filter(Q(projectrole__project=OuterRef('pk')) |
                      Q(publication__projects=OuterRef('pk')))
              .order_by()
              .values(_grp=Value(1))               # group by a constant -> one row
              .annotate(_c=Count('pk', distinct=True))
              .values('_c')[:1])
    return Coalesce(Subquery(people, output_field=IntegerField()), 0)

class ProjectRoleInline(admin.TabularInline):
    model = ProjectRole
    extra = 1  # Number of extra forms displayed

    autocomplete_fields = ['person']

    # This method is used to customize the form field for a given database field
    def formfield_for_dbfield(self, db_field, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, **kwargs)
        # If the database field is 'role', we create a new Textarea widget with the desired 
        # number of columns and rows
        if db_field.name == 'role':
            formfield.widget = forms.Textarea(attrs={'cols': '40', 'rows': '2'})
        return formfield
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Order by end_date descending with nulls first
        return qs.order_by(F('end_date').desc(nulls_first=True))

class BannerInline(ImageCroppingMixin, admin.StackedInline):
    """This allows us to edit Banner from the Project page"""
    model = Banner
    extra = 1  # Number of extra "empty" forms to show at the bottom

class PhotoInline(ImageCroppingMixin, admin.StackedInline):
    """This allows us to add Photos from the Project page"""
    model = Photo
    extra = 0  # Number of extra "empty" forms to show at the bottom

class GrantInline(admin.TabularInline):
    model = Grant.projects.through
    extra = 1

class ProjectAliasInline(admin.TabularInline):
    """Former URL slugs that 301-redirect to this project (#944).

    Rows appear automatically when a project's short_name is changed (see
    Project.save()); editors can also add historical aliases by hand here so old
    links keep resolving."""
    model = ProjectAlias
    extra = 0
    fields = ['slug', 'created']
    readonly_fields = ['created']
    verbose_name = "Former slug (redirect)"
    verbose_name_plural = "Former slugs (redirect to this project)"

@admin.register(Project, site=ml_admin_site)
class ProjectAdmin(ImageCroppingMixin, admin.ModelAdmin):
    # Search by name plus the research-area facets editors think in (umbrella, keyword).
    search_fields = ['name', 'short_name', 'project_umbrellas__name', 'keywords__keyword']
    ordering = ('name',)  # deterministic alphabetical sort (matched the autocomplete already)
    inlines = [GrantInline, BannerInline, PhotoInline, ProjectRoleInline, ProjectAliasInline]

    # The list display lets us control what is shown in the Project table at Home > Website > Project
    # info on displaying multiple entries comes from http://stackoverflow.com/questions/9164610/custom-columns-using-django-admin
    # The count / most-recent-artifact columns read annotations set in
    # get_queryset() (sortable) rather than the per-row model methods (#1346).
    list_display = ('name', 'is_visible', 'get_display_thumbnail', 'start_date', 'end_date', 'has_ended',
                    'contributor_count', 'people_count',
                    'current_member_count', 'past_member_count',
                    'most_recent_artifact_date', 'most_recent_artifact_type',
                    'pub_count', 'video_count', 'talk_count', 'banner_count')

    # Bounds the per-row gallery-image filesystem check on the changelist (#1346).
    list_per_page = 50

    # Toggle public/private right in the list (is_visible renders as the plain
    # checkbox formfield_for_dbfield defines below). 'name' stays the row link.
    list_editable = ('is_visible',)

    actions = ('make_public', 'make_private')

    fieldsets = [
        (None,                      {'fields': ['name', 'display_short_name', 'short_name', 'is_visible']}),
        ('About',                   {'fields': ['start_date', 'end_date', 'summary', 'about', 'gallery_image', 'cropping', 'thumbnail_alt_text']}),
        ('Links',                   {'fields': ['website', 'data_url', 'featured_video', 'featured_code_repo_url']}),
        ('Associations',            {'fields': ['project_umbrellas', 'keywords']}),
    ]
    
    list_filter = (ActiveProjectsFilter, 'is_visible')

    def get_queryset(self, request):
        """Collapse the Project changelist's ~10 per-row count/aggregate columns
        into a single query (#1346). Each count is an independent scalar subquery
        (see related_count_subquery), so the joins don't multiply each other; the
        three most-recent-artifact dates are scalar subqueries combined into one
        sortable date. With the default 100 projects this turns ~1,000+ queries
        into a handful.

        The model methods (get_publication_count, get_most_recent_artifact, ...)
        are left intact for the public site / detail views; only the changelist
        columns are repointed at these annotations.
        """
        def latest_artifact_date(model):
            # Most recent artifact date for this project, as a scalar subquery.
            return Subquery(
                model.objects.filter(projects=OuterRef('pk'))
                .order_by('-date').values('date')[:1]
            )

        return (super().get_queryset(request).annotate(
            _pub_count=related_count_subquery(Publication, 'projects'),
            _talk_count=related_count_subquery(Talk, 'projects'),
            _video_count=related_count_subquery(Video, 'projects'),
            _banner_count=related_count_subquery(Banner, 'project'),
            _people_count=related_count_subquery(
                ProjectRole, 'project', count_field='person', distinct=True),
            _current_member_count=related_count_subquery(
                ProjectRole, 'project', count_field='person', distinct=True,
                extra_filter=Q(end_date__isnull=True)),
            _past_member_count=related_count_subquery(
                ProjectRole, 'project', count_field='person', distinct=True,
                extra_filter=Q(end_date__isnull=False)),
            _contributor_count=_contributor_count_subquery(),
            _pub_max_date=latest_artifact_date(Publication),
            _talk_max_date=latest_artifact_date(Talk),
            _video_max_date=latest_artifact_date(Video),
        ).annotate(
            # Greatest ignores NULLs on Postgres, so this is the max of whichever
            # artifact types exist (NULL only when the project has none).
            _recent_artifact_date=Greatest(
                '_pub_max_date', '_talk_max_date', '_video_max_date'),
        ))

    # --- Annotation-backed changelist columns (sortable; see get_queryset) ---

    def pub_count(self, obj):
        return obj._pub_count
    pub_count.short_description = 'Pubs'
    pub_count.admin_order_field = '_pub_count'

    def video_count(self, obj):
        return obj._video_count
    video_count.short_description = 'Videos'
    video_count.admin_order_field = '_video_count'

    def talk_count(self, obj):
        return obj._talk_count
    talk_count.short_description = 'Talks'
    talk_count.admin_order_field = '_talk_count'

    def banner_count(self, obj):
        return obj._banner_count
    banner_count.short_description = 'Banners'
    banner_count.admin_order_field = '_banner_count'

    def people_count(self, obj):
        return obj._people_count
    people_count.short_description = 'Num People'
    people_count.admin_order_field = '_people_count'

    def current_member_count(self, obj):
        return obj._current_member_count
    current_member_count.short_description = 'Num Current Members'
    current_member_count.admin_order_field = '_current_member_count'

    def past_member_count(self, obj):
        return obj._past_member_count
    past_member_count.short_description = 'Num Past Members'
    past_member_count.admin_order_field = '_past_member_count'

    def contributor_count(self, obj):
        return obj._contributor_count
    contributor_count.short_description = 'Contributors'
    contributor_count.admin_order_field = '_contributor_count'

    def most_recent_artifact_date(self, obj):
        return obj._recent_artifact_date
    most_recent_artifact_date.short_description = 'Most Recent Artifact Date'
    most_recent_artifact_date.admin_order_field = '_recent_artifact_date'

    def most_recent_artifact_type(self, obj):
        """Type ('Publication' / 'Talk' / 'Video') of the most recent artifact,
        derived from the three annotated max-dates. Ties resolve in the same
        order as Project.get_most_recent_artifact (pub, then talk, then video)."""
        candidates = [('Publication', obj._pub_max_date),
                      ('Talk', obj._talk_max_date),
                      ('Video', obj._video_max_date)]
        candidates = [(label, d) for label, d in candidates if d is not None]
        if not candidates:
            return None
        return max(candidates, key=lambda c: c[1])[0]
    most_recent_artifact_type.short_description = 'Most Recent Artifact Type'

    def get_display_thumbnail(self, obj):
        if obj.gallery_image and os.path.isfile(obj.gallery_image.path):
            # Use easy_thumbnails to generate a thumbnail
            thumbnailer = get_thumbnailer(obj.gallery_image)
            thumbnail_options = {'size': (PROJECT_THUMBNAIL_SIZE[0], PROJECT_THUMBNAIL_SIZE[1]), 'crop': True}
            thumbnail_url = thumbnailer.get_thumbnail(thumbnail_options).url

            return format_html('<img src="{}" height="50" style="border-radius: 5%;"/>', thumbnail_url)
        return 'No Thumbnail'
    
    get_display_thumbnail.short_description = 'Thumbnail'

    def get_search_results(self, request, queryset, search_term):
        """In this code, get_search_results is a method that Django calls to get the list of results 
        for the autocomplete dropdown. By overriding this method, you can modify the queryset that 
        Django uses to populate the dropdown. The line queryset = queryset.order_by('name') sorts 
        the projects by name"""
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        queryset = queryset.order_by('name')
        return queryset, use_distinct

    def formfield_for_dbfield(self, db_field, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, **kwargs)
        if db_field.name == 'summary':
            formfield.widget = forms.Textarea(attrs={'rows': 3, 'class': 'vLargeTextField'})
        if db_field.name == 'is_visible':
            # is_visible is a nullable BooleanField (NULL = legacy, pre-backfill;
            # see Project model / #1300), which Django would otherwise render as a
            # three-state Yes/No/Unknown select. Editors only ever want public vs
            # private, so present a plain checkbox; unchecked saves False (private).
            formfield = forms.BooleanField(
                required=False,
                label=db_field.verbose_name,
                help_text=db_field.help_text,
            )
        return formfield

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        if db_field.name == "keywords":
            kwargs["widget"] = widgets.FilteredSelectMultiple("keywords", is_stacked=False)
        if db_field.name == "project_umbrellas":
            kwargs["widget"] = widgets.FilteredSelectMultiple("project umbrellas", is_stacked=False)
        return super(ProjectAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)
    
    def changelist_view(self, request, extra_context=None):
        if not request.GET:
            q = request.GET.copy()
            q['active_project_status'] = 'Active'
            request.GET = q
            request.META['QUERY_STRING'] = request.GET.urlencode()
        return super(ProjectAdmin,self).changelist_view(request, extra_context=extra_context)

    @admin.action(description='Mark selected projects as public (visible)')
    def make_public(self, request, queryset):
        updated = queryset.update(is_visible=True)
        self.message_user(request, f'{updated} project(s) marked public.')

    @admin.action(description='Mark selected projects as private (hidden)')
    def make_private(self, request, queryset):
        updated = queryset.update(is_visible=False)
        self.message_user(request, f'{updated} project(s) marked private.')
