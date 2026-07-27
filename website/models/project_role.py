from django.db import models
from datetime import date, datetime, timedelta

class LeadProjectRoleTypes(models.TextChoices):
    PI = ('PI', 'Principal Investigator')
    CO_PI = ('Co-PI', 'Co-PI')
    STUDENT_LEAD = 'Student Lead'
    POSTDOC_LEAD = 'Postdoc Lead'
    RESEARCH_SCIENTIST_LEAD = 'Research Scientist Lead'

class ProjectRole(models.Model):
    person = models.ForeignKey("Person", on_delete=models.CASCADE)
    project = models.ForeignKey("Project", on_delete=models.CASCADE)
    
    role = models.TextField(blank=True, null=True)
    role.help_text = ("A brief description of your role on the project. Be specific. If you had more than one" 
                      " role (e.g., you started as a dev and then became a lead), please add a new role with"
                      " the correct start and end dates")
    
    start_date = models.DateField()
    start_date.help_text = "When did you start in this role?"
   
    end_date = models.DateField(blank=True, null=True)
    end_date.help_text = ("When did you end this role? Leave blank if you are still working on this project."
                          "Note: we will automatically set this end date if a project has been ended.")
    
    LEAD_PROJECT_ROLE_MAPPING = {
        LeadProjectRoleTypes.PI: 0,
        LeadProjectRoleTypes.CO_PI: 1,
        LeadProjectRoleTypes.STUDENT_LEAD: 2,
        LeadProjectRoleTypes.POSTDOC_LEAD: 3,
        LeadProjectRoleTypes.RESEARCH_SCIENTIST_LEAD: 4,
        "Other": 5
    }

    lead_project_role = models.CharField(max_length=50, blank=True, null=True, choices=LeadProjectRoleTypes.choices, default=None)
    lead_project_role.help_text = ("If you are the lead student on this project, please select 'Student Lead.'"
                                   " In addition, for most projects, Jon Froehlich should be the PI. So make sure" 
                                   " to add him on his person page.")

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
        """
        Returns a string representation of the date range.

        If only the start date is provided, the returned string is in the format 'YYYY-'.
        If both start and end dates are provided and they are in the same year, the returned string is 'YYYY'.
        If both start and end dates are provided and they are in different years, the returned string is 'YYYY-YYYY'.

        Returns:
            str: A string representation of the date range.
        """
        if self.start_date is not None and self.end_date is None:
            return f"{self.start_date.year}-"
        elif self.start_date is not None and self.end_date is not None and self.start_date.year == self.end_date.year:
            return f"{self.start_date.year}"
        else:
            return f"{self.start_date.year}-{self.end_date.year}"

    def get_position_during_role(self):
        """Returns the Position this person held when they started this project role.

        This is deliberately *not* the person's current title: a 2015 undergrad
        who is now a professor should read "Undergrad" next to a 2015 project
        stint (see issue #1426). Where someone's title changed mid-stint (an
        undergrad who stayed on for an MS), we report what they were when they
        joined the project.

        Resolution order, most to least faithful:

        1. The latest-starting Position whose date range contains this role's
           ``start_date``.
        2. Failing that, the latest-starting Position that had already begun by
           ``start_date`` (the role started in a gap between positions).
        3. Failing that, the earliest Position (the role predates every recorded
           position -- data drift, common for older imported roles).
        4. ``None`` only if the person has no Positions at all.

        Filters ``position_set`` in Python rather than issuing a query, so a
        caller with ``prefetch_related('person__position_set')`` (e.g. the API's
        project-people endpoint) resolves this with zero extra queries. This
        mirrors :meth:`Person.get_latest_position`; positions-per-person is tiny.

        Example:
            >>> role.get_position_during_role().title
            'Undergrad'
        """
        positions = list(self.person.position_set.all())
        if not positions:
            return None

        containing = [p for p in positions
                      if p.start_date <= self.start_date
                      and (p.end_date is None or p.end_date >= self.start_date)]
        if containing:
            return max(containing, key=lambda p: p.start_date)

        already_started = [p for p in positions if p.start_date <= self.start_date]
        if already_started:
            return max(already_started, key=lambda p: p.start_date)

        return min(positions, key=lambda p: p.start_date)

    def get_pi_status_index(self):
        if self.lead_project_role is not None and self.lead_project_role in self.LEAD_PROJECT_ROLE_MAPPING:
            return self.LEAD_PROJECT_ROLE_MAPPING[self.lead_project_role]
        else:
            return self.LEAD_PROJECT_ROLE_MAPPING["Other"]

    def is_active(self):
        return self.start_date is not None and self.start_date <= date.today() and \
               (self.end_date is None or self.end_date >= date.today())
    
    def has_role_started(self):
        return self.start_date is not None and self.start_date <= date.today()

    def has_completed_role(self):
        """Returns true if this role is completed (as of today). That is, if end_date < date.today()"""
        if self.end_date is None:
            return False
        else:
            return self.end_date < date.today()

    # This function is used to differentiate between past and future roles
    def is_past(self):
        return self.start_date is not None and self.start_date < date.today() and \
               (self.end_date is not None and self.end_date < date.today())

    def __str__(self):
        return "Project: '{}' Name={}, StartDate={} EndDate={} PI/Co-PI={}, PI Status Index={} Title Index={}".format(
            self.project.name, self.person.get_full_name(), self.start_date, self.end_date,
            self.lead_project_role, self.get_pi_status_index(), self.person.get_current_title_index)