from django.contrib import admin
from website.models import Grant, GrantTrackingLink
from django.db.models import Sum
from website.admin import ArtifactAdmin
from website.admin.admin_site import ml_admin_site

@admin.register(Grant, site=ml_admin_site)
class GrantAdmin(ArtifactAdmin):

    # Fields and columns only the superuser may see (#1448). Editors (PhD
    # students / staff) hold `view_grant` so they can look up a UW worktag, but
    # funding data and the proposal files were the reason Grant was superuser-only
    # in the first place (#1125), so those stay hidden. Enforced in
    # get_fieldsets / get_list_display / changelist_view below, and pinned by
    # website/tests/test_grant_tracking.py.
    SUPERUSER_ONLY_FIELDS = ('funding_amount', 'pdf_file', 'raw_file')

    # search_fields are used for auto-complete, see:
    #   https://docs.djangoproject.com/en/3.0/ref/contrib/admin/#django.contrib.admin.ModelAdmin.autocomplete_fields
    # Dropped 'date' (string-searching a DateField is unhelpful); added PI/Co-PI
    # (author) and sponsor name so grants are findable by people and funder.
    # The UW codes are searchable too — pasting a worktag from an email into the
    # search box is the main way this page gets used (#1448).
    search_fields = ['title', 'forum_name', 'authors__first_name',
                     'authors__last_name', 'sponsor__name',
                     'uw_grant_id', 'uw_award_number', 'uw_award_name']

    # The list display lets us control what is shown in the default talk table at Home > Website > Grants
    # See: https://docs.djangoproject.com/en/dev/ref/contrib/admin/#django.contrib.admin.ModelAdmin.list_display
    list_display = ('title', 'date', 'get_first_author_last_name', 'sponsor',
                    'uw_grant_id', 'funding_amount')

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
        ('UW Internal Tracking',    {'fields': ['uw_grant_id', 'uw_award_number', 'uw_award_name'],
                                     'description': 'UW/Workday administrative codes for this award. '
                                                    'These are <b>internal</b>: they are never shown on the '
                                                    'public site and are deliberately excluded from the REST API.'}),
        ('Grant Files',             {'fields': ['pdf_file', 'raw_file']}),
        ('Project Info',            {'fields': ['projects', 'project_umbrellas']}),
        ('Keyword Info',            {'fields': ['keywords']}),
    ]

    def get_fieldsets(self, request, obj=None):
        """Drop the funding/file fields for non-superusers.

        Editors get `view_grant` only, so Django already renders this form
        read-only; this narrows *what* they can read. Any section left empty
        (i.e. 'Grant Files') disappears entirely rather than rendering a header
        with nothing under it.
        """
        fieldsets = super().get_fieldsets(request, obj)
        if request.user.is_superuser:
            return fieldsets

        visible = []
        for name, options in fieldsets:
            fields = [f for f in options['fields']
                      if f not in self.SUPERUSER_ONLY_FIELDS]
            if fields:
                # New dict per request — never mutate the class-level fieldsets.
                visible.append((name, {**options, 'fields': fields}))
        return visible

    def get_list_display(self, request):
        """Same boundary as get_fieldsets, applied to the changelist columns."""
        list_display = super().get_list_display(request)
        if request.user.is_superuser:
            return list_display
        return tuple(column for column in list_display
                     if column not in self.SUPERUSER_ONLY_FIELDS)

    def changelist_view(self, request, extra_context=None):
        """
        Override the changelist view to include total funding amount and the
        official UW tracking links.

        Both are superuser-only: the funding rollup is the aggregate of the data
        we hide per-row from Editors, and the tracking links point at the
        maintainer's personal financial-reporting systems (#1448).
        """
        # Get the base queryset (respects any active filters)
        response = super().changelist_view(request, extra_context)

        # Only proceed if we have a context (not a redirect response)
        if hasattr(response, 'context_data') and request.user.is_superuser:
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
            response.context_data['grant_tracking_links'] = GrantTrackingLink.objects.all()

        return response

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        def tweak(field_name, **attrs):
            """Apply label/help_text overrides to a field if this form has it.

            Non-superusers get a reduced fieldset (see get_fieldsets), so the
            funding and file fields are simply absent from their form — look
            them up defensively rather than KeyError-ing on a view-only render.
            """
            field = form.base_fields.get(field_name)
            if field is None:
                return
            for attr, value in attrs.items():
                setattr(field, attr, value)

        tweak('authors',
              label='PIs and Co-PIs',
              help_text="The first author is assumed to be the PI. Co-PIs should be listed in the order they appear on the grant.")

        tweak('date', label='Start date', help_text='Start date for the grant')

        grant_url = "https://www.nsf.gov/awardsearch/showAward?AWD_ID=1302338"
        tweak('forum_url',
              label='Grant url',
              help_text=f'The grant url (e.g., <a href="{grant_url}">{grant_url}</a>)')

        # NB: 'grant_id' is disambiguated from 'UW Grant ID (worktag)' by a
        # verbose_name on the model, not here — a label set on the form is
        # ignored when Django renders the read-only view Editors get.

        tweak('pdf_file',
              label='Grant PDF',
              help_text='The rendered PDF of the grant. Internal only. This is not currently shown on the website.')
        tweak('raw_file',
              help_text='The raw file (e.g., Word Docx, Overleaf Zip, etc.) for <b>archival</b> purposes. This is not shown on the website.')

        tweak('projects',
              help_text='Associate this grant with all the projects that it supports.')

        funding_amount = form.base_fields.get('funding_amount')
        if funding_amount is not None:
            funding_amount.widget.attrs['style'] = 'min-width: 300px;'

        return form
