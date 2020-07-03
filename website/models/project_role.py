from django.db import models

from .person import Person
from .project import Project

class Project_Role(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    role = models.TextField(blank=True, null=True)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    PI = "PI"
    CoPI = "Co-PI"

    PIMEMBER_CHOICES = (
        (PI, "PI"),
        (CoPI, "Co-PI")
    )

    PI_MEMBER_MAPPING = {
        PI: 0,
        CoPI: 1,
        "Other": 2
    }

    pi_member = models.CharField(max_length=50, blank=True, null=True, choices=PIMEMBER_CHOICES, default=None)

    def get_start_date_short(self):
        return self.start_date.strftime('%b %Y')

    def get_end_date_short(self):
        # if this project role has no end date, check to see if the project itself has ended
        # and use the end date for that instead
        # See: https://github.com/jonfroehlich/makeabilitylabwebsite/issues/836
        if self.end_date is None and self.project.has_ended():
            return self.project.end_date.strftime('%b %Y')
        elif self.end_date is None:
            return "Present" # project is still active and role has no end date
        else:
            return self.end_date.strftime('%b %Y')

    def get_date_range_as_str(self):
        if self.start_date is not None and self.end_date is None:
            return "{}-".format(self.start_date.year)
        elif self.start_date is not None and self.end_date is not None and self.start_date.year == self.end_date.year:
            return "{}".format(self.start_date.year)
        else:
            return "{}-{}".format(self.start_date.year, self.end_date.year)

    def get_pi_status_index(self):
        if self.pi_member is not None and self.pi_member in self.PI_MEMBER_MAPPING:
            return self.PI_MEMBER_MAPPING[self.pi_member]
        else:
            return self.PI_MEMBER_MAPPING["Other"]

    def is_active(self):
        return self.start_date is not None and self.start_date <= date.today() and \
               (self.end_date is None or self.end_date >= date.today())

    # This function is used to differentiate between past and future roles
    def is_past(self):
        return self.start_date is not None and self.start_date < date.today() and \
               (self.end_date is not None and self.end_date < date.today())

    def __str__(self):
        return "Project: '{}' Name={}, StartDate={} EndDate={} PI/Co-PI={}, PI Status Index={} Title Index={}".format(
            self.project.name, self.person.get_full_name(), self.start_date, self.end_date,
            self.pi_member, self.get_pi_status_index(), self.person.get_current_title_index())