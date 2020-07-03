from django.db import models
from django.core.exceptions import ValidationError

from datetime import date, datetime, timedelta

from .person import Person

class Position(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
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
        UGRAD: 7,
        HIGH_SCHOOL: 8,
        UNKNOWN: 9
    }

    CURRENT_MEMBER = "Current Member"
    PAST_MEMBER = "Past Member"
    CURRENT_COLLABORATOR = "Current Collaborator"
    PAST_COLLABORATOR = "Past Collaborator"

    department = models.CharField(max_length=50, blank=True, default="Computer Science")
    school = models.CharField(max_length=60, default="University of Washington")

    def get_start_date_short(self):
        earliest_position = self.person.get_earliest_position_in_role(self.role, contiguous_constraint=True)
        return earliest_position.start_date.strftime('%b %Y')

    def get_end_date_short(self):
        return self.end_date.strftime('%b %Y') if self.end_date is not None else "Present"

    # Returns an abbreviated version of the department field
    def get_department_abbreviated(self):
        department_keywords_normal = ["building science", "architecture", "bioengineering"]
        department_keywords_map = ["BuildSci", "Arch", "BIOE"]
        abbrv = ""
        if "computer science" in self.department.lower() and "engineering" in self.department.lower():
            abbrv += 'CSE,'
        elif "computer science" in self.department.lower():
            abbrv += 'CS,'
        elif 'computer engineering' in self.department.lower():
            abbrv += 'CprE,'

        if "information" in self.department.lower() or "ischool" in self.department.lower():
            abbrv += 'iSchool,'

        if "hcde" in self.department.lower() or "human centered design" in self.department.lower() and "engineering" in self.department.lower():
            abbrv += 'HCDE,'

        for keyword in department_keywords_normal:
            counter = 0
            if keyword in self.department.lower():
                abbrv += department_keywords_map[counter]
                counter += 1

        if abbrv.__len__() > 0:
            return abbrv[:abbrv.__len__() - 1]
        else:
            return "".join(e[0] for e in self.department.split(" "))

    def get_title_index(self):
        if self.title in self.TITLE_ORDER_MAPPING:
            return self.TITLE_ORDER_MAPPING[self.title]
        else:
            return self.TITLE_ORDER_MAPPING[self.UNKNOWN]

    # Returns a timedelta object of total time in this position
    def get_time_in_this_position(self):
        if self.end_date is not None and self.start_date is not None:
            return self.end_date - self.start_date
        elif self.end_date is None and self.start_date is not None:
            return date.today() - self.start_date
        else:
            return None

    # Returns the start and end dates as strings
    def get_date_range_as_str(self):
        if self.start_date is not None and self.end_date is None:
            return "{}-".format(self.start_date.year)
        elif self.start_date is not None and self.end_date is not None and self.start_date.year == self.end_date.year:
            return "{}".format(self.start_date.year)
        else:
            return "{}-{}".format(self.start_date.year, self.end_date.year)

    # Returns true if collaborator
    def is_collaborator(self):
        return self.role == Position.COLLABORATOR

    # Returns true if member
    def is_member(self):
        return self.role == Position.MEMBER

    # Returns true if professor
    def is_professor(self):
        return self.title == Position.FULL_PROF or self.title == Position.ASSOCIATE_PROF or self.title == Position.ASSISTANT_PROF

    # Returns true if grad student
    def is_grad_student(self):
        return self.title == Position.MS_STUDENT or self.title == Position.PHD_STUDENT

    # Returns true if high school student
    def is_high_school(self):
        return self.title == Position.HIGH_SCHOOL

    # Returns true if member is current based on end date
    def is_current_member(self):
        return self.is_member() and \
               self.start_date is not None and self.start_date <= date.today() and \
               (self.end_date is None or (self.end_date is not None and self.end_date >= date.today()))

    # Returns true if member is current based on end date
    def is_current_collaborator(self):
        return self.is_collaborator() and \
               (self.start_date is not None and self.start_date <= date.today() and \
                self.end_date is None or (self.end_date is not None and self.end_date >= date.today()))

    # Returns true if collaborator is a past collaborator (used to differentiate between future collaborators)
    def is_past_collaborator(self):
        return self.is_collaborator() and \
               self.start_date < date.today() and \
               self.end_date != None and self.end_date < date.today()

    # Returns true if member is an alumni member (used to differentiate between future members)
    def is_alumni_member(self):
        return self.is_member() and \
               self.start_date < date.today() and \
               self.end_date != None and self.end_date < date.today()

    # Automatically called by Django when saving data to validate the data
    def clean(self):
        if self.end_date is not None and self.start_date > self.end_date:
            raise ValidationError('The start date must be before the end date')

    def __str__(self):
        return "Name={}, Role={}, Title={}, Start={} End={}".format(
            self.person.get_full_name(), self.role, self.title, self.start_date, self.end_date)