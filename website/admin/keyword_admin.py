from django.contrib import admin
from website.models import (Keyword, Publication, Talk, Poster, Grant,
                            Project, ProjectUmbrella)
from website.admin.utils import related_count_subquery
from website.admin.admin_site import ml_admin_site

# Every model that has a `keywords` M2M to Keyword. Used to compute a keyword's
# *total* usage so the "Unused" filter is trustworthy: keywords lives on Artifact
# (Publication/Talk/Poster/Grant), Project, and ProjectUmbrella. (Video is not an
# Artifact, so it has no keywords.)
KEYWORD_USERS = (Publication, Talk, Poster, Grant, Project, ProjectUmbrella)


class KeywordUsageFilter(admin.SimpleListFilter):
    """Filter keywords by whether anything references them — the core
    taxonomy-cleanup need: find orphan tags to delete (#1346). Reads the
    _total_usage annotation set in KeywordAdmin.get_queryset."""
    title = 'usage'
    parameter_name = 'usage'

    def lookups(self, request, model_admin):
        return (('unused', 'Unused (0 references)'), ('used', 'Used'))

    def queryset(self, request, queryset):
        if self.value() == 'unused':
            return queryset.filter(_total_usage=0)
        if self.value() == 'used':
            return queryset.filter(_total_usage__gt=0)
        return queryset


@admin.register(Keyword, site=ml_admin_site)
class KeywordAdmin(admin.ModelAdmin):
    list_display = ['keyword', 'project_count', 'publication_count', 'total_usage']

    # The keyword table had no search box; alphabetical ordering also groups
    # near-duplicate tags (e.g. "Speech" / "speech") adjacently for cleanup.
    search_fields = ['keyword']
    ordering = ['keyword']
    list_filter = (KeywordUsageFilter,)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Add projects and publications to the context. We then use this extra data in
        the change_form.html template to display the projects and publications that use this keyword.
        This change_form.html template is found in website/admin/templates/admin/website/keyword/change_form.html
        """
        extra_context = extra_context or {}
        keyword = Keyword.objects.get(pk=object_id)
        extra_context['projects'] = keyword.project_set.all().order_by('-start_date')
        extra_context['publications'] = keyword.publication_set.all().order_by('-date')
        return super().change_view(
            request, object_id, form_url, extra_context=extra_context,
        )

    def get_queryset(self, request):
        """Annotate each keyword with project/publication counts plus a *total*
        usage across all referencing models. Each count is an independent scalar
        subquery (related_count_subquery) — summing several Count() joins in one
        query would multiply rows and miscount; this stays correct and sortable.
        """
        return super().get_queryset(request).annotate(
            _project_count=related_count_subquery(Project, 'keywords'),
            _publication_count=related_count_subquery(Publication, 'keywords'),
            _total_usage=sum(
                (related_count_subquery(model, 'keywords') for model in KEYWORD_USERS),
                start=0,
            ),
        )

    def project_count(self, obj):
        """Return the number of projects that use keyword"""
        return obj._project_count
    project_count.admin_order_field = '_project_count'

    def publication_count(self, obj):
        """Return the number of publications that use this keyword"""
        return obj._publication_count
    publication_count.admin_order_field = '_publication_count'

    def total_usage(self, obj):
        """Total references across publications, talks, posters, grants, projects,
        and project umbrellas (0 == an orphan keyword safe to delete)."""
        return obj._total_usage
    total_usage.short_description = 'Total Uses'
    total_usage.admin_order_field = '_total_usage'
