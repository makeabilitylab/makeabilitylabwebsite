from django import forms
from django.contrib import admin
from website.models import Award
from website.admin.admin_site import ml_admin_site


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

    # NOTE: `recipients` and `projects` are SortedManyToManyFields, so they render
    # with sortedm2m's default ordered widget out of the box. To match the
    # filter-horizontal widget used for authors elsewhere (the repo's
    # sortedm2m_filter_horizontal_widget), mirror the setup in person_admin.py.