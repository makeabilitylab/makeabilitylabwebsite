from django.db import models
from sortedm2m.fields import SortedManyToManyField


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

    def get_recipient_names(self):
        """Returns a comma-separated list of recipient names (no middle names)."""
        return ", ".join(p.get_full_name(include_middle=False) for p in self.recipients.all())

    get_recipient_names.short_description = "Recipients"

    def get_project_names(self):
        """Returns a comma-separated list of honored project names."""
        return ", ".join(proj.name for proj in self.projects.all())

    get_project_names.short_description = "Projects"

    def get_honorees(self):
        """Returns a combined, human-readable list of recipients and projects."""
        parts = [self.get_recipient_names(), self.get_project_names()]
        return ", ".join(part for part in parts if part)

    def __str__(self):
        return f"{self.get_honorees() or 'Unknown'} — {self.title} ({self.date.year})"

    class Meta:
        ordering = ['-date']