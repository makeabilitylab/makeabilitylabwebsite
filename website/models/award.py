from django.db import models
from sortedm2m.fields import SortedManyToManyField

from image_cropping import ImageRatioField

from website.utils.fileutils import UniquePathAndRename
from website.utils.upload_validators import validate_image_upload


class AwardType(models.TextChoices):
    """The section an award appears under on the public Awards page.

    Declaration order below IS the display order of the sections. The stored
    value is the short string on the left; the label on the right is shown both
    in the admin dropdown and as the section heading (hence the plural form).
    """
    STUDENT_AWARD = "Student Award", "Student Awards"
    PHD_FELLOWSHIP = "PhD Fellowship", "PhD Fellowships"
    FACULTY_HONOR = "Faculty Honor", "Faculty Honors"
    PROJECT_AWARD = "Project Award", "Project Awards"


class Award(models.Model):
    """An external recognition or distinction earned by lab member(s) and/or a project.

    Examples:
      - A PhD fellowship (NSF GRFP, Google PhD Fellowship, Microsoft Research)
      - A faculty honor (SIGCHI Societal Impact, COE Outstanding Faculty)
      - A student award (dissertation award, student innovator award)
      - A project award (Project Sidewalk / HydroSense competition wins)

    An award must honor at least one recipient (Person) and/or one project, and
    must have an award_type (which determines its section). Both rules are
    enforced by AwardAdminForm / the field options in award_admin.py.

    Paper-level awards are NOT stored here; those live on ``Publication.award``.
    """
    recipients = SortedManyToManyField('Person', blank=True)
    recipients.help_text = "Lab member(s) honored by this award. Leave blank for a project-only award."

    projects = SortedManyToManyField('Project', blank=True)
    projects.help_text = "Project(s) honored by this award. Leave blank for a person-only award."

    title = models.CharField(max_length=255)
    title.help_text = "Name of the award, e.g., 'NSF Graduate Research Fellowship'."

    organization = models.CharField(max_length=255, blank=True, null=True)
    organization.help_text = "The awarding organization, e.g., 'NSF', 'ACM SIGCHI', 'Google'."

    date = models.DateField()
    date.help_text = "When the award was received. Only the year is displayed, but a full date is required for sorting."

    # Required for data entry (blank=False) but kept nullable at the DB level
    # (null=True) on purpose: changing it then never triggers a NOT NULL
    # migration on the already-populated table, which matters because this
    # project generates and applies migrations per-environment at deploy time.
    award_type = models.CharField(max_length=50, choices=AwardType.choices, null=True)
    award_type.help_text = "Which section this award appears under on the Awards page (required)."

    url = models.URLField(blank=True, null=True)
    url.help_text = "Optional link to the award announcement or details."

    description = models.TextField(blank=True, null=True)
    description.help_text = "Optional additional context. HTML is allowed."

    # Optional emblem/logo for the left-side "anchor" the Awards page shows next
    # to each award (see display_award_snippet.html / get_anchor_kind). It mainly
    # serves Faculty Honors, which otherwise fall back to a medal icon; uploading
    # one here overrides the per-category default for any award.
    badge = models.ImageField(blank=True, null=True, upload_to=UniquePathAndRename("awards", True),
                              max_length=255, validators=[validate_image_upload])
    badge.help_text = ("Optional emblem/logo shown beside the award (e.g., the awarding "
                       "organization's logo). Faculty honors otherwise show a medal icon. "
                       "Student awards default to the recipient's photo and project awards to "
                       "the project thumbnail; uploading a badge overrides those.")

    # Square crop box for the badge, applied on the public Awards page so every
    # anchor (badge, portrait, project thumbnail, medal) reads as a uniform square
    # tile. Stored as an "x1,y1,x2,y2" string; the admin shows a Cropper.js preview
    # before the first save (same pattern as Person.cropping / Sponsor.icon_cropping).
    badge_cropping = ImageRatioField('badge', '245x245', size_warning=True)
    badge_cropping.help_text = ("Crop the badge to a square using the preview above "
                                "(no need to save first). Keeps award anchors uniform.")

    badge_alt_text = models.CharField(max_length=255, blank=True, null=True)
    badge_alt_text.help_text = "Alt text for the badge image. Defaults to the award title if left blank."

    def get_recipient_names(self):
        """Returns a comma-separated list of recipient names (no middle names)."""
        return ", ".join(p.get_full_name(include_middle=False) for p in self.recipients.all())

    get_recipient_names.short_description = "Recipients"

    def get_project_names(self):
        """Returns a comma-separated list of honored project names."""
        return ", ".join(proj.name for proj in self.projects.all())

    get_project_names.short_description = "Projects"

    def get_visible_projects(self):
        """
        Returns the honored projects that are publicly visible (#1300).

        Used by the public award snippet so a private project is not mentioned
        on the Awards page. The admin-facing get_project_names() intentionally
        still lists all projects.
        """
        return self.projects.filter(is_visible=True)

    def get_honorees(self):
        """Returns a combined, human-readable list of recipients and projects."""
        parts = [self.get_recipient_names(), self.get_project_names()]
        return ", ".join(part for part in parts if part)

    def get_badge_alt_text(self):
        """Alt text for the badge image; falls back to the award title."""
        return self.badge_alt_text or self.title

    def get_portrait_person(self):
        """First recipient (in sorted order) who has an uploaded photo.

        Drives the Student-award "portrait" anchor on the Awards page. Iterates
        recipients.all() rather than filtering so the editor-controlled
        SortedManyToManyField order is honored.
        """
        for person in self.recipients.all():
            if person.image:
                return person
        return None

    def get_thumbnail_project(self):
        """First publicly-visible project (in sorted order) with a gallery image.

        Drives the Project-award "thumbnail" anchor on the Awards page.
        """
        for project in self.get_visible_projects():
            if project.gallery_image:
                return project
        return None

    def get_anchor_kind(self):
        """Which left-side visual the Awards page shows for this award.

        Returns one of:
          'badge'     - an uploaded emblem/logo (overrides everything),
          'portrait'  - a recipient's photo (Student Awards / PhD Fellowships),
          'thumbnail' - a project's gallery image (Project Awards),
          'medal'     - an icon fallback (Faculty Honors, or when the
                        category-specific image is missing).
        """
        if self.badge:
            return 'badge'
        if self.award_type in (AwardType.STUDENT_AWARD, AwardType.PHD_FELLOWSHIP):
            if self.get_portrait_person():
                return 'portrait'
        elif self.award_type == AwardType.PROJECT_AWARD:
            if self.get_thumbnail_project():
                return 'thumbnail'
        return 'medal'

    def __str__(self):
        return f"{self.get_honorees() or 'Unknown'} — {self.title} ({self.date.year})"

    class Meta:
        ordering = ['-date']