from django.db import models
from django.core.exceptions import ValidationError

from datetime import date, datetime, timedelta

import website.utils.ml_utils as ml_utils # for department abbreviations
from enum import Enum

# from .person import Person
class AbstractedTitle(Enum):
    """Enum class for abstracted titles"""
    GRADUATE_STUDENT = "Graduate Student"
    PROFESSOR = "Professor"
    PROFESSIONAL = "Professional"

class MemberClassification(Enum):
    """Enum class for member or collaborator classification"""
    CURRENT_MEMBER = "Current Member"
    PAST_MEMBER = "Alumni Member"
    FUTURE_MEMBER = "Future Member"
    CURRENT_COLLABORATOR = "Current Collaborator"
    PAST_COLLABORATOR = "Past Collaborator"

class Role(models.TextChoices):
    MEMBER = "Member"
    COLLABORATOR = "Collaborator"

class Title(models.TextChoices):
    HIGH_SCHOOL = "High School Student"
    UGRAD = "Undergrad"
    MS_STUDENT = "MS Student"
    PHD_STUDENT = "PhD Student"
    POST_DOC = "Post doc"
    DIRECTOR = "Director"
    ASSISTANT_PROF = "Assistant Professor"
    ASSOCIATE_PROF = "Associate Professor"
    FULL_PROF = "Professor"
    RESEARCH_SCIENTIST = "Research Scientist"
    SOFTWARE_DEVELOPER = "Software Developer"
    DESIGNER = "Designer"
    UNKNOWN = "Uncategorized"

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
    role = models.CharField(max_length=50, choices=Role.choices, default=Role.MEMBER)
    title = models.CharField(max_length=50, choices=Title.choices)

    department = models.CharField(max_length=50, blank=True, default="Allen School of Computer Science and Engineering")
    school = models.CharField(max_length=60, default="University of Washington")

    TITLE_ORDER_MAPPING = {
        Title.FULL_PROF: 0,
        Title.ASSOCIATE_PROF: 1,
        Title.ASSISTANT_PROF: 2,
        Title.POST_DOC: 3,
        Title.DIRECTOR: 4,
        Title.RESEARCH_SCIENTIST: 5,
        Title.PHD_STUDENT: 6,
        Title.MS_STUDENT: 7,
        Title.SOFTWARE_DEVELOPER: 8,
        Title.DESIGNER: 8,
        Title.UGRAD: 9,
        Title.HIGH_SCHOOL: 10,
        Title.UNKNOWN: 11
    }

    def get_start_date_short(self):
        earliest_position = self.person.get_earliest_position_in_role(self.role, contiguous_constraint=True)
        return earliest_position.start_date.strftime('%b %Y')

    def get_end_date_short(self):
        return self.end_date.strftime('%b %Y') if self.end_date is not None else "Present"
    
    def get_school_abbreviated(self):
        """Returns an abbreviated version of the school field"""
        return ml_utils.get_school_abbreviated(self.school)

    def get_department_abbreviated(self):
        """Returns an abbreviated version of the department field"""
        return ml_utils.get_department_abbreviated(self.department)

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
        return self.role == Role.COLLABORATOR

    def is_member(self):
        """Returns true if member"""
        return self.role == Role.MEMBER

    def is_professor(self):
        """Returns true if professor"""
        return (self.title == Title.FULL_PROF or 
                self.title == Title.ASSOCIATE_PROF or 
                self.title == Title.ASSISTANT_PROF)

    def is_grad_student(self):
        """Returns true if grad student"""
        return (self.title == Title.MS_STUDENT or 
                self.title == Title.PHD_STUDENT)

    def is_high_school(self):
        """Returns true if high school student"""
        return self.title == Title.HIGH_SCHOOL

    def is_current_member(self):
        """Returns true if member is current based on end date"""
        has_started = self.start_date is not None and self.start_date <= date.today()
        has_not_ended = self.end_date is None or self.end_date >= date.today()

        return self.is_member() and has_started and has_not_ended

    def is_current_collaborator(self):
        """Returns true if member is current based on end date"""
        has_started = self.start_date is not None and self.start_date <= date.today()
        has_not_ended = self.end_date is None or self.end_date >= date.today()

        return self.is_collaborator() and has_started and has_not_ended
    
    def is_past_collaborator(self):
        """Returns true if collaborator is a past collaborator (used to differentiate between future collaborators)"""
        is_collaborator = self.is_collaborator()
        has_started = self.start_date < date.today()
        has_ended = self.end_date is not None and self.end_date < date.today()

        return is_collaborator and has_started and has_ended

    def is_alumni_member(self):
        """Returns true if member is an alumni member (used to differentiate between future members)"""
        is_member = self.is_member()
        has_started = self.start_date < date.today()
        has_ended = self.end_date is not None and self.end_date < date.today()

        return is_member and has_started and has_ended

    def clean(self):
        """Automatically called by Django when saving data to validate the data"""
        if self.end_date is not None and self.start_date > self.end_date:
            raise ValidationError('The start date must be before the end date')

    def __str__(self):
        return "Name={}, Role={}, Title={}, Start={} End={}".format(
            self.person.get_full_name(), self.role, self.title, self.start_date, self.end_date)
    
    @staticmethod
    def get_sorted_abstracted_titles():
        """Static method returns a sorted list of abstracted title names"""
        return (AbstractedTitle.PROFESSOR.value, AbstractedTitle.PROFESSIONAL.value, Title.POST_DOC,
                AbstractedTitle.GRADUATE_STUDENT.value, Title.UGRAD, Title.HIGH_SCHOOL, Title.UNKNOWN)

    @staticmethod
    def get_map_abstracted_title_to_order():
        """Static method returns a map of abstracted titles to their order"""
        sorted_abstracted_titles = Position.get_sorted_abstracted_titles()
        map_title_to_order = {j: i for i, j in enumerate(sorted_abstracted_titles)}
        return map_title_to_order

    @staticmethod
    def get_abstracted_title(position):
        """Static method returns an abstracted title for a given position
           For example, if you pass "Assistant Professor" it will return "Professor"
           or if you pass "PhD Student" it will return "Graduate Student"
        """

        if(type(position) is Position):
            position = position.title # get the title str from position object

        if Position.is_graduate_student_position(position):
            return AbstractedTitle.GRADUATE_STUDENT.value
        elif Position.is_professorial_position(position):
            return AbstractedTitle.PROFESSOR.value
        elif Position.is_professional_position(position):
            return AbstractedTitle.PROFESSIONAL.value
        else:
            return position

    @staticmethod
    def get_prof_titles():
        """Returns an array of professor titles"""
        return [Title.ASSISTANT_PROF, Title.ASSOCIATE_PROF, Title.FULL_PROF]

    @staticmethod
    def get_sorted_titles():
        """Static method returns a sorted list of title names"""
        return sorted(Title, key=lambda title: Position.TITLE_ORDER_MAPPING[title])

    @staticmethod
    def get_map_title_to_order():
        """Static method returns a map of titles to their order"""
        return Position.TITLE_ORDER_MAPPING

    @staticmethod
    def is_graduate_student_position(position):
        """Static method returns true if position is a graduated student"""
        if(type(position) is Position):
            return (position.title == Title.PHD_STUDENT or 
                    position.title == Title.MS_STUDENT)
        elif(type(position) is str):
            return (position == Title.PHD_STUDENT or 
                    position == Title.MS_STUDENT)
        else:
            raise TypeError("position must be of type Position or str")

    @staticmethod
    def is_professorial_position(position):
        """Static method returns true if position is a professor"""
        if(type(position) is Position):
            return (position.title == Title.FULL_PROF or 
                    position.title == Title.ASSOCIATE_PROF or
                    position.title == Title.ASSISTANT_PROF)
        elif(type(position) is str):
            return (position == Title.FULL_PROF or 
                    position == Title.ASSOCIATE_PROF or
                    position == Title.ASSISTANT_PROF)  
        else:
            raise TypeError("position must be of type Position or str")
        
    @staticmethod
    def is_professional_position(position):
        """Static method returns true if position is a professional"""
        if(type(position) is Position):
            return (position.title == Title.RESEARCH_SCIENTIST or 
                    position.title == Title.SOFTWARE_DEVELOPER or
                    position.title == Title.DIRECTOR or 
                    position.title == Title.DESIGNER)
        elif(type(position) is str):
            return (position == Title.RESEARCH_SCIENTIST or 
                    position == Title.SOFTWARE_DEVELOPER or
                    position == Title.DIRECTOR or
                    position == Title.DESIGNER)
        else:
            raise TypeError("position must be of type Position or str")
    