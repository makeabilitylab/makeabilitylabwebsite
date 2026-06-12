from django import forms
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from website.models import Award
from website.admin.admin_site import ml_admin_site
from sortedm2m_filter_horizontal_widget.forms import SortedFilteredSelectMultiple


class AwardAdminForm(forms.ModelForm):
    class Meta:
        model = Award
        fields = '__all__'

    def clean(self):
        """An award must honor at least one recipient (Person) and/or one project.
        This lives on the form (not Model.clean) because M2M values are only
        available here in cleaned_data; on the model they aren't set until after
        the first save."""
        cleaned_data = super().clean()
        recipients = cleaned_data.get('recipients')
        projects = cleaned_data.get('projects')
        if not recipients and not projects:
            raise forms.ValidationError(
                "An award must honor at least one recipient (Person) or project."
            )
        return cleaned_data


@admin.register(Award, site=ml_admin_site)
class AwardAdmin(admin.ModelAdmin):
    form = AwardAdminForm

    # get_recipient_names / get_project_names are methods on the Award model;
    # their column headers come from each method's short_description.
    list_display = ('title', 'organization', 'date',
                    'get_recipient_names', 'get_project_names', 'award_type')

    list_filter = ('award_type', 'date')

    search_fields = ('title', 'organization',
                     'recipients__first_name', 'recipients__last_name',
                     'projects__name')

    ordering = ('-date',)

    def get_fieldsets(self, request, obj=None):
        # Built at request time so reverse() can resolve the Publications admin URL.
        publications_url = reverse('admin:website_publication_changelist')
        intro = format_html(
            'Congrats on the award! 🎉 '
            '<br><br>'
            'Use this page for <strong>people and project awards</strong>: fellowships, '
            'faculty/student honors, society recognitions, project awards, and the like.'
            '<br><br>'
            'Do not enter <strong>Best Paper, Honorable Mention, or other paper awards here.</strong> '
            'Those live on the publication itself (its <em>Award</em> field) &mdash; '
            '<a href="{}">go to Publications</a>.'
            '<br><br>',
            publications_url
        )
        return [
            (None, {
                'fields': ['title', 'date', 'organization', 'award_type'],
                'description': intro,
            }),
            ('Honorees', {
                'fields': ['recipients', 'projects'],
                'description': 'Attach at least one person and/or project. A single '
                               'award can honor both (e.g., a PI and their project).',
            }),
            ('Links & Details', {
                'fields': ['url', 'description'],
            }),
        ]

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """
        Use the two-panel sorted filter widget for the recipients and projects fields.

        This replaces the default sortedm2m checkbox list with a filter_horizontal
        style interface that's much easier to use with 100s of recipients and projects.
        """
        if db_field.name == 'recipients' or db_field.name == 'projects':
            kwargs['widget'] = SortedFilteredSelectMultiple()
        return super().formfield_for_manytomany(db_field, request, **kwargs)