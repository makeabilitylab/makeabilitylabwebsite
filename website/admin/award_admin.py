import os

from django import forms
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from easy_thumbnails.files import get_thumbnailer
from image_cropping import ImageCroppingMixin
from website.models import Award
from website.admin.admin_site import ml_admin_site
from website.utils.fileutils import pad_image_to_square
from sortedm2m_filter_horizontal_widget.forms import SortedFilteredSelectMultiple


class AwardAdminForm(forms.ModelForm):
    # When set, a non-square badge upload is padded to a centered square on save
    # instead of being cropped to one (#1410). See AwardAdmin.save_model and
    # website.utils.fileutils.pad_image_to_square for the why/how; the live
    # admin preview is driven by pad_to_square.js / pad_to_square.css.
    pad_badge_to_square = forms.BooleanField(
        required=False,
        initial=True,
        label="Pad badge to a square (don't crop)",
        help_text=(
            "If the uploaded badge isn't square, add blank margins to make it "
            "square instead of cropping it — keeping the whole image, "
            "centered. Margins are transparent for PNG/WebP and white for JPEG. "
            "Uncheck to crop to a square with the tool above instead."
        ),
    )

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
class AwardAdmin(ImageCroppingMixin, admin.ModelAdmin):
    form = AwardAdminForm

    class Media:
        # Drives the "pad to square" toggle: hides the cropper and shows an
        # object-fit:contain preview when padding is selected (#1410).
        js = ("website/js/pad_to_square.js",)
        css = {"all": ("website/css/pad_to_square.css",)}

    # get_recipient_names / get_project_names are methods on the Award model;
    # their column headers come from each method's short_description.
    list_display = ('title', 'get_display_thumbnail', 'organization', 'date',
                    'get_recipient_names', 'get_project_names', 'award_type')

    list_filter = ('award_type', 'date')

    search_fields = ('title', 'organization',
                     'recipients__first_name', 'recipients__last_name',
                     'projects__name')

    ordering = ('-date',)

    date_hierarchy = 'date'  # Year/month/day drill-down (awards are browsed by year)

    # Prefetch the M2M relations get_recipient_names / get_project_names walk, so
    # they don't fire two queries per award on the changelist (#1346).
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('recipients', 'projects')

    def save_model(self, request, obj, form, change):
        """Optionally pad a freshly uploaded badge to a centered square instead
        of cropping it (#1410).

        The badge is cropped to a 1:1 square on the public Awards page. When
        "pad to square" is checked and a new, non-square badge was uploaded, we
        pad it here with white/transparent margins (see ``pad_image_to_square``)
        and store a full-image crop box, so the square comes from padding rather
        than from chopping off content. When unchecked — or when the badge
        wasn't changed — nothing happens and the interactive cropper above
        behaves exactly as before.
        """
        if (form.cleaned_data.get('pad_badge_to_square')
                and 'badge' in form.changed_data and obj.badge):
            result = pad_image_to_square(obj.badge)
            if result is not None:
                content, box = result
                obj.badge.save(content.name, content, save=False)
                obj.badge_cropping = box
        super().save_model(request, obj, form, change)

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
            ('Display', {
                'fields': ['badge', 'pad_badge_to_square', 'badge_cropping',
                           'badge_alt_text'],
                'description': 'Optional. On the Awards page, faculty honors show a medal icon, '
                               'student awards show the recipient’s photo, and project awards '
                               'show the project thumbnail. Upload a badge/logo here to override '
                               'that with a custom emblem (e.g., the awarding org’s logo).',
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

    def get_display_thumbnail(self, obj):
        """Square preview of the uploaded badge (with its crop applied) in the
        changelist, mirroring the SponsorAdmin/NewsAdmin logo columns. Awards
        without a custom badge fall back to a medal icon on the public page, so
        there's nothing to show here."""
        if obj.badge and os.path.isfile(obj.badge.path):
            thumbnailer = get_thumbnailer(obj.badge)
            options = {'size': (50, 50), 'crop': True, 'box': obj.badge_cropping}
            thumbnail_url = thumbnailer.get_thumbnail(options).url
            return format_html('<img src="{}" height="50" width="50" '
                               'style="object-fit: cover; border-radius: 5%;"/>', thumbnail_url)
        return '—'

    get_display_thumbnail.short_description = 'Badge'