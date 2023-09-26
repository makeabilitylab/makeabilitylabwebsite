from django.db import models
from django.core.exceptions import ValidationError

from datetime import date, datetime, timedelta

# from .person import Person

class Position(models.Model):

    # For ForeignKey, not using the class name Person but rather the string 'Person'
    # so we don't have circular dependencies, see: https://docs.djangoproject.com/en/dev/ref/models/fields/#foreignkey
    # and https://stackoverflow.com/a/8466752
    person = models.ForeignKey('Person', on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    advisor = models.ForeignKey('Person', blank=True, null=True, related_name='Advisor', on_delete=models.SET_NULL)
    co_advisor = models.ForeignKey('Person', blank=True, null=True, related_name='Co_Advisor', verbose_name='Co-advisor', on_delete=models.SET_NULL)
    grad_mentor = models.ForeignKey('Person', blank=True, null=True, related_name='Grad_Mentor', on_delete=models.SET_NULL)


    # According to Django docs, best to have field choices within the primary
    # class that uses them. See https://docs.djangoproject.com/en/1.9/ref/models/fields/#choices
    MEMBER = "Member"
    COLLABORATOR = "Collaborator"

    ROLE_CHOICES = (
        (MEMBER, "Member"),
        (COLLABORATOR, "Collaborator"),
    )
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default=MEMBER)

    # Note, if you add a new title here, you must also update:
    #  1. The TITLE_ORDER_MAPPING below
    #  2. The static method get_sorted_titles
    HIGH_SCHOOL = "High School Student"
    UGRAD = "Undergrad"
    MS_STUDENT = "MS Student"
    PHD_STUDENT = "PhD Student"
    POST_DOC = "Post doc"
    ASSISTANT_PROF = "Assistant Professor"
    ASSOCIATE_PROF = "Associate Professor"
    FULL_PROF = "Professor"
    RESEARCH_SCIENTIST = "Research Scientist"
    SOFTWARE_DEVELOPER = "Software Developer"
    DESIGNER = "Designer"
    UNKNOWN = "Uncategorized"

    TITLE_CHOICES = (
        (HIGH_SCHOOL, HIGH_SCHOOL),
        (UGRAD, UGRAD),
        (MS_STUDENT, MS_STUDENT),
        (PHD_STUDENT, PHD_STUDENT),
        (POST_DOC, POST_DOC),
        (ASSISTANT_PROF, ASSISTANT_PROF),
        (ASSOCIATE_PROF, ASSOCIATE_PROF),
        (FULL_PROF, FULL_PROF),
        (RESEARCH_SCIENTIST, RESEARCH_SCIENTIST),
        (SOFTWARE_DEVELOPER, SOFTWARE_DEVELOPER),
        (DESIGNER, DESIGNER),
        (UNKNOWN, UNKNOWN)
    )
    title = models.CharField(max_length=50, choices=TITLE_CHOICES)

    TITLE_ORDER_MAPPING = {
        FULL_PROF: 0,
        ASSOCIATE_PROF: 1,
        ASSISTANT_PROF: 2,
        POST_DOC: 3,
        RESEARCH_SCIENTIST: 4,
        PHD_STUDENT: 5,
        MS_STUDENT: 6,
        SOFTWARE_DEVELOPER: 6,
        DESIGNER: 6,
        UGRAD: 7,
        HIGH_SCHOOL: 8,
        UNKNOWN: 9
    }

    CURRENT_MEMBER = "Current Member"
    PAST_MEMBER = "Past Member"
    FUTURE_MEMBER = "Future Member"
    CURRENT_COLLABORATOR = "Current Collaborator"
    PAST_COLLABORATOR = "Past Collaborator"

    department = models.CharField(max_length=50, blank=True, default="Computer Science")
    school = models.CharField(max_length=60, default="University of Washington")

    def get_start_date_short(self):
        earliest_position = self.person.get_earliest_position_in_role(self.role, contiguous_constraint=True)
        return earliest_position.start_date.strftime('%b %Y')

    def get_end_date_short(self):
        return self.end_date.strftime('%b %Y') if self.end_date is not None else "Present"

    def get_department_abbreviated(self):
        """Returns an abbreviated version of the department field"""
        dept_low = self.department.lower();

        if "computer science" in dept_low and "engineering" in dept_low:
            return 'CSE'
        elif "computer science" in dept_low:
            return 'CS'
        elif 'computer engineering' in dept_low:
            return 'CprE'
        elif "information" in dept_low or "ischool" in dept_low:
            return 'iSchool'
        elif "hcde" in dept_low or "human centered design" in dept_low and "engineering" in dept_low:
            return 'HCDE'
        elif "building science" in dept_low:
            return 'BuildSci'
        elif "architecture" in dept_low:
            return 'Arch'
        elif "bioengineering" in dept_low:
            return 'BioE'
        elif self.department is not None:
            return self.department[:3]
        else:
            return ""
        
    def get_sorted_titles():
        """Static method returns a sorted list of title names"""
        return ("Professor", Position.RESEARCH_SCIENTIST, Position.POST_DOC, 
                Position.SOFTWARE_DEVELOPER, Position.DESIGNER, Position.PHD_STUDENT, 
                Position.MS_STUDENT, Position.UGRAD, Position.HIGH_SCHOOL, Position.UNKNOWN)

    def get_title_index(self):
        """Returns the index from TITLE_ORDER_MAPPING for the current title"""
        if self.title in self.TITLE_ORDER_MAPPING:
            return self.TITLE_ORDER_MAPPING[self.title]
        else:
            return self.TITLE_ORDER_MAPPING[self.UNKNOWN]

    def get_time_in_this_position(self):
        """Returns a timedelta object of total time in this position"""
        if self.end_date is not None and self.start_date is not None:
            return self.end_date - self.start_date
        elif self.end_date is None and self.start_date is not None:
            return date.today() - self.start_date
        else:
            return None

    def get_date_range_as_str(self):
        """Returns the start and end dates as strings"""
        if self.start_date is not None and self.end_date is None:
            return "{}-".format(self.start_date.year)
        elif self.start_date is not None and self.end_date is not None and self.start_date.year == self.end_date.year:
            return "{}".format(self.start_date.year)
        else:
            return "{}-{}".format(self.start_date.year, self.end_date.year)

    def is_collaborator(self):
        """Returns true if collaborator"""
        return self.role == Position.COLLABORATOR

    def is_member(self):
        """Returns true if member"""
        return self.role == Position.MEMBER

    def is_professor(self):
        """Returns true if professor"""
        return self.title == Position.FULL_PROF or self.title == Position.ASSOCIATE_PROF or self.title == Position.ASSISTANT_PROF

    def is_grad_student(self):
        """Returns true if grad student"""
        return self.title == Position.MS_STUDENT or self.title == Position.PHD_STUDENT

    def is_high_school(self):
        """Returns true if high school student"""
        return self.title == Position.HIGH_SCHOOL

    def is_current_member(self):
        """Returns true if member is current based on end date"""
        return self.is_member() and \
               self.start_date is not None and self.start_date <= date.today() and \
               (self.end_date is None or (self.end_date is not None and self.end_date >= date.today()))

    def is_current_collaborator(self):
        """Returns true if member is current based on end date"""
        return self.is_collaborator() and \
               (self.start_date is not None and self.start_date <= date.today() and \
                self.end_date is None or (self.end_date is not None and self.end_date >= date.today()))

    def is_past_collaborator(self):
        """Returns true if collaborator is a past collaborator (used to differentiate between future collaborators)"""
        return self.is_collaborator() and \
               self.start_date < date.today() and \
               self.end_date != None and self.end_date < date.today()

    def is_alumni_member(self):
        """Returns true if member is an alumni member (used to differentiate between future members)"""
        return self.is_member() and \
               self.start_date < date.today() and \
               self.end_date != None and self.end_date < date.today()

    def clean(self):
        """Automatically called by Django when saving data to validate the data"""
        if self.end_date is not None and self.start_date > self.end_date:
            raise ValidationError('The start date must be before the end date')

    def __str__(self):
        return "Name={}, Role={}, Title={}, Start={} End={}".format(
            self.person.get_full_name(), self.role, self.title, self.start_date, self.end_date)