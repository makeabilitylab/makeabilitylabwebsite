from django.db import models
from sortedm2m.fields import SortedManyToManyField


class PersonAwardType(models.TextChoices):
    FELLOWSHIP = "Fellowship"
    FACULTY_HONOR = "Faculty Honor"
    SERVICE_AWARD = "Service Award"
    DISSERTATION_AWARD = "Dissertation Award"
    OTHER = "Other"


class PersonAward(models.Model):
    """A non-publication award or distinction earned by one or more lab members.

    Examples: a fellowship (NSF GRFP, Google PhD Fellowship), a faculty honor
    (UW Allen School Outstanding Faculty Award), or a society recognition
    (SIGCHI Social Impact Award).

    Paper-level awards are NOT stored here; those live on ``Publication.award``.
    """
    recipients = SortedManyToManyField('Person', blank=True)
    recipients.help_text = "The lab member(s) who received this award."

    title = models.CharField(max_length=255)
    title.help_text = "Name of the award, e.g., 'NSF Graduate Research Fellowship'."

    organization = models.CharField(max_length=255, blank=True, null=True)
    organization.help_text = "The awarding organization, e.g., 'NSF', 'ACM SIGCHI', 'Google'."

    date = models.DateField()
    date.help_text = "When the award was received. Only the year is displayed, but a full date is required for sorting."

    award_type = models.CharField(max_length=50, choices=PersonAwardType.choices, blank=True, null=True)
    award_type.help_text = "Optional category, used for grouping and iconography."

    url = models.URLField(blank=True, null=True)
    url.help_text = "Optional link to the award announcement or details."

    description = models.TextField(blank=True, null=True)
    description.help_text = "Optional additional context. HTML is allowed."

    def get_recipient_names(self):
        """Returns a comma-separated list of recipient names (no middle names)."""
        return ", ".join(p.get_full_name(include_middle=False) for p in self.recipients.all())

    get_recipient_names.short_description = "Recipients"

    def __str__(self):
        return f"{self.get_recipient_names() or 'Unknown'} — {self.title} ({self.date.year})"

    class Meta:
        ordering = ['-date']
        verbose_name = "Person Award"
