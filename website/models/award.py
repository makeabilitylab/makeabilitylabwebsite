from django.db import models
from sortedm2m.fields import SortedManyToManyField


class AwardType(models.TextChoices):
    FELLOWSHIP = "Fellowship"
    FACULTY_HONOR = "Faculty Honor"
    SERVICE_AWARD = "Service Award"
    DISSERTATION_AWARD = "Dissertation Award"
    PROJECT_AWARD = "Project Award"
    OTHER = "Other"


class Award(models.Model):
    """An external recognition or distinction earned by lab member(s) and/or a project.

    Examples:
      - A person fellowship (NSF GRFP, Google PhD Fellowship)
      - A faculty honor (UW Allen School Outstanding Faculty Award)
      - A society recognition (SIGCHI Social Impact Award)
      - A project award (Project Sidewalk recognized by a civic-tech org)

    An award should honor at least one recipient (Person) and/or one project; that
    rule is enforced by AwardAdminForm in award_admin.py (M2M data isn't available
    during Model.clean() on first save, so the check has to live on the form).

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

    award_type = models.CharField(max_length=50, choices=AwardType.choices, blank=True, null=True)
    award_type.help_text = "Optional category, used for grouping and iconography."

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