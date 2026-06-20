from django.contrib import admin, messages
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.db import transaction
from django.shortcuts import render
from website.models import (Keyword, Publication, Talk, Poster, Grant,
                            Project, ProjectUmbrella)
from website.admin.utils import related_count_subquery
from website.admin.admin_site import ml_admin_site

# Every model that has a `keywords` M2M to Keyword. Used to compute a keyword's
# *total* usage so the "Unused" filter is trustworthy: keywords lives on Artifact
# (Publication/Talk/Poster/Grant), Project, and ProjectUmbrella. (Video is not an
# Artifact, so it has no keywords.)
KEYWORD_USERS = (Publication, Talk, Poster, Grant, Project, ProjectUmbrella)

# Reverse accessor on Keyword for each model in KEYWORD_USERS — the relations a
# merge must walk to reattach the target keyword before deleting the sources.
KEYWORD_REVERSE_ACCESSORS = (
    'publication_set', 'talk_set', 'poster_set',
    'grant_set', 'project_set', 'projectumbrella_set',
)


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


@transaction.atomic
def merge_keywords_into_target(target, sources):
    """Reassign every reference from ``sources`` onto ``target``, then delete the
    sources. Returns the number of source keywords removed.

    For each source keyword and each model that references keywords, every
    tagged object gains the target via ``obj.keywords.add(target)`` — idempotent,
    so an object already tagged with the target ends up with a single row, not a
    duplicate. Deleting the source then drops its own M2M rows, so no explicit
    ``remove()`` is needed. ``target`` is skipped if present in ``sources``.

    Runs in a transaction: a failure mid-merge rolls back rather than leaving the
    taxonomy half-merged.
    """
    removed = 0
    for source in sources:
        if source.pk == target.pk:
            continue
        for accessor in KEYWORD_REVERSE_ACCESSORS:
            for obj in getattr(source, accessor).all():
                obj.keywords.add(target)
        source.delete()
        removed += 1
    return removed


@admin.register(Keyword, site=ml_admin_site)
class KeywordAdmin(admin.ModelAdmin):
    list_display = ['keyword', 'project_count', 'publication_count', 'total_usage']

    # The keyword table had no search box; alphabetical ordering also groups
    # near-duplicate tags (e.g. "Speech" / "speech") adjacently for cleanup.
    search_fields = ['keyword']
    ordering = ['keyword']
    list_filter = (KeywordUsageFilter,)
    actions = ['merge_keywords']

    @admin.action(description='Merge selected keywords (dedup taxonomy)')
    def merge_keywords(self, request, queryset):
        """Merge two or more keywords into one chosen target (#1352).

        Two-step Django action: the first click shows an intermediate page to
        pick which selected keyword to keep as the target; confirming reassigns
        every reference onto it (across all six keyword-holding models) and
        deletes the others. Destructive, so it always routes through the
        confirmation page — it never merges on the first click.
        """
        selected = list(queryset.order_by('keyword'))
        if len(selected) < 2:
            self.message_user(
                request,
                "Select two or more keywords to merge.",
                level=messages.WARNING,
            )
            return None

        if request.POST.get('confirm_merge'):
            target = next((k for k in selected
                           if str(k.pk) == request.POST.get('target')), None)
            if target is None:
                self.message_user(
                    request,
                    "Pick which keyword to keep as the merge target.",
                    level=messages.WARNING,
                )
            else:
                sources = [k for k in selected if k.pk != target.pk]
                source_names = ', '.join(f'"{k.keyword}"' for k in sources)
                removed = merge_keywords_into_target(target, sources)
                self.message_user(
                    request,
                    f'Merged {removed} keyword(s) ({source_names}) into '
                    f'"{target.keyword}".',
                    level=messages.SUCCESS,
                )
                return None  # back to the changelist

        # First click (or a target wasn't chosen): show the confirmation page,
        # annotating each candidate with its total usage to inform the choice.
        candidates = [
            {'keyword': k, 'total_uses': sum(
                getattr(k, accessor).count()
                for accessor in KEYWORD_REVERSE_ACCESSORS)}
            for k in selected
        ]
        context = {
            **self.admin_site.each_context(request),
            'title': 'Merge keywords',
            'candidates': candidates,
            'selected_ids': [str(k.pk) for k in selected],
            'action_checkbox_name': ACTION_CHECKBOX_NAME,
            'opts': self.model._meta,
        }
        return render(
            request,
            'admin/website/keyword/merge_keywords.html',
            context,
        )

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
