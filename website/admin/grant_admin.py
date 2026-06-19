from django.contrib import admin
from website.models import Grant
from django.db.models import Sum
from website.admin import ArtifactAdmin
from website.admin.admin_site import ml_admin_site

@admin.register(Grant, site=ml_admin_site)
class GrantAdmin(ArtifactAdmin):

    # search_fields are used for auto-complete, see:
    #   https://docs.djangoproject.com/en/3.0/ref/contrib/admin/#django.contrib.admin.ModelAdmin.autocomplete_fields
    # Dropped 'date' (string-searching a DateField is unhelpful); added PI/Co-PI
    # (author) and sponsor name so grants are findable by people and funder.
    search_fields = ['title', 'forum_name', 'authors__first_name',
                     'authors__last_name', 'sponsor__name']

    # The list display lets us control what is shown in the default talk table at Home > Website > Grants
    # See: https://docs.djangoproject.com/en/dev/ref/contrib/admin/#django.contrib.admin.ModelAdmin.list_display
    list_display = ('title', 'date', 'get_first_author_last_name', 'sponsor', 'funding_amount')

    # I want to make sponsor auto-complete but it's causing errors, so commenting out
    # https://github.com/makeabilitylab/makeabilitylabwebsite/issues/1093
    # Update: After upgrading to Django 5.2.9, this seems to work again!
    autocomplete_fields = ['sponsor']

    ordering = ('-date',)  # sort by date, most recent first
    date_hierarchy = 'date'  # Year/month/day drill-down by grant start date

    # sponsor is a FK column -> list_select_related (Django applies it to the
    # changelist query); the get_first_author_last_name column walks authors ->
    # prefetch in get_queryset. Together these drop the per-row queries (#1346).
    list_select_related = ('sponsor',)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('authors')

    fieldsets = [
        (None,                      {'fields': ['title', 'authors']}),
        ('Grant Info',              {'fields': ['date', 'end_date', 'sponsor', 'funding_amount', 'forum_url', 'grant_id']}),
        ('Grant Files',             {'fields': ['pdf_file', 'raw_file']}),
        ('Project Info',            {'fields': ['projects', 'project_umbrellas']}),
        ('Keyword Info',            {'fields': ['keywords']}),
    ]

    def changelist_view(self, request, extra_context=None):
        """
        Override the changelist view to include total funding amount.
        
        This calculates the sum of all funding_amount values and passes it
        to the template context for display at the top of the grants list.
        """
        # Get the base queryset (respects any active filters)
        response = super().changelist_view(request, extra_context)
        
        # Only proceed if we have a context (not a redirect response)
        if hasattr(response, 'context_data'):
            # Get the filtered queryset from the changelist
            cl = response.context_data.get('cl')
            if cl:
                queryset = cl.queryset
            else:
                queryset = self.get_queryset(request)
            
            # Calculate total funding from the (possibly filtered) queryset
            total = queryset.aggregate(
                total_funding=Sum('funding_amount')
            )['total_funding'] or 0
            
            response.context_data['total_funding'] = total
        
        return response

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        form.base_fields['authors'].label = 'PIs and Co-PIs'
        form.base_fields['authors'].help_text = "The first author is assumed to be the PI. Co-PIs should be listed in the order they appear on the grant."

        form.base_fields['date'].label = 'Start date'
        form.base_fields['date'].help_text = 'Start date for the grant'

        form.base_fields['forum_url'].label = 'Grant url'
        grant_url = "https://www.nsf.gov/awardsearch/showAward?AWD_ID=1302338"
        form.base_fields['forum_url'].help_text = f'The grant url (e.g., <a href="{grant_url}">{grant_url}</a>)'

        form.base_fields['pdf_file'].label = 'Grant PDF'
        form.base_fields['pdf_file'].help_text = 'The rendered PDF of the grant. Internal only. This is not currently shown on the website.'
        form.base_fields['raw_file'].help_text = 'The raw file (e.g., Word Docx, Overleaf Zip, etc.) for <b>archival</b> purposes. This is not shown on the website.'

        form.base_fields['projects'].help_text = 'Associate this grant with all the projects that it supports.'

        form.base_fields['funding_amount'].widget.attrs['style'] = f'min-width: 300px;'

        return form