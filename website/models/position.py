from django.db import models
from django.core.exceptions import ValidationError
from website.models.project_role import ProjectRole
from datetime import date, datetime, timedelta

import website.utils.ml_utils as ml_utils # for department abbreviations
from enum import Enum

import logging # for logging

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

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
    MEDICAL_DOCTOR = "Medical Doctor"     
    MEDICAL_STUDENT = "Medical Student"
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
        Title.MEDICAL_DOCTOR: 6,
        Title.PHD_STUDENT: 7,
        Title.MEDICAL_STUDENT: 8,
        Title.MS_STUDENT: 9,
        Title.SOFTWARE_DEVELOPER: 10,
        Title.DESIGNER: 11,
        Title.UGRAD: 12,
        Title.HIGH_SCHOOL: 13,
        Title.UNKNOWN: 14
    }

    # BETTER - Use class constant:
    PROFESSOR_TITLES = {Title.FULL_PROF, Title.ASSOCIATE_PROF, Title.ASSISTANT_PROF}
    GRAD_STUDENT_TITLES = {Title.MS_STUDENT, Title.PHD_STUDENT, Title.MEDICAL_STUDENT}

    def save(self, *args, **kwargs):
        # Save the Position instance first
        super(Position, self).save(*args, **kwargs)  

        # If the person has completely left the lab (there have no active Positions),
        # then we need to also set the the end_date of all ProjectRoles related to the Person
        # This is just a convenience method to make sure that project roles are properly ended 
        # when a person leaves the lab.
        if self.end_date and self.person.is_active == False:
            # Get ProjectRoles related to the Person that have a null end_date
            project_roles_to_close = ProjectRole.objects.filter(person=self.person, end_date__isnull=True)
            
            # Log the ProjectRoles that will be automatically closed
            for project_role in project_roles_to_close:
                # Use the earlier of the project's end_date and the position's end_date
                end_date = min(project_role.project.end_date, self.end_date) if project_role.project.end_date else self.end_date
                
                _logger.info(f"Automatically closing ProjectRole: {project_role.id} for Person: {self.person.id} with end_date: {end_date}")
                
                # Update end_date of the ProjectRole
                project_role.end_date = end_date
                project_role.save()

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
            return self.TITLE_ORDER_MAPPING[Title.UNKNOWN]

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
        """Returns True if this position is a professor."""
        return self.title in self.PROFESSOR_TITLES

    def is_grad_student(self):
        """Returns True if this position is a grad student."""
        return self.title in self.GRAD_STUDENT_TITLES

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

    def has_started(self):
        """Returns true if the person has started"""
        return self.start_date is not None and self.start_date <= date.today()
    
    def clean(self):
        """Automatically called by Django when saving data to validate the data"""
        if self.end_date is not None and self.start_date > self.end_date:
            raise ValidationError('The start date must be before the end date')

    def __str__(self):
        return "Name={}, Role={}, Title={}, Start={} End={}".format(
            self.person.get_full_name(), self.role, self.title, self.start_date, self.end_date)
    
    # In position.py, add to the Position class:

    @staticmethod
    def get_indefinite_article_for_title(title):
        """
        Returns the appropriate indefinite article ('a' or 'an') for a given title.
        
        Args:
            title: Title enum value or string
            
        Returns:
            'a' or 'an' depending on whether the title starts with a vowel sound
            
        Example:
            >>> Position.get_indefinite_article(Title.UGRAD)
            'an'
            >>> Position.get_indefinite_article(Title.PHD_STUDENT)
            'a'
        """
        # Titles that require "an" (start with vowel sound)
        titles_needing_an = {
            Title.UGRAD,           # "Undergrad"
            Title.MS_STUDENT,      # "MS Student" (M sounds like "em")
            Title.ASSISTANT_PROF,  # "Assistant Professor"
            Title.ASSOCIATE_PROF,  # "Associate Professor"
        }
        
        return "an" if title in titles_needing_an else "a"

    @staticmethod
    def get_sorted_abstracted_titles():
        """Static method returns a sorted list of abstracted title names"""
        return (AbstractedTitle.PROFESSOR.value, Title.POST_DOC,
                AbstractedTitle.GRADUATE_STUDENT.value, Title.UGRAD, 
                Title.HIGH_SCHOOL, 
                AbstractedTitle.PROFESSIONAL.value,
                Title.UNKNOWN)

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
                    position.title == Title.MS_STUDENT or
                    position.title == Title.MEDICAL_STUDENT)
        elif(type(position) is str):
            return (position == Title.PHD_STUDENT or 
                    position == Title.MS_STUDENT or
                    position == Title.MEDICAL_STUDENT)
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
                    position.title == Title.DESIGNER or
                    position.title == Title.MEDICAL_DOCTOR)
        elif(type(position) is str):
            return (position == Title.RESEARCH_SCIENTIST or 
                    position == Title.SOFTWARE_DEVELOPER or
                    position == Title.DIRECTOR or
                    position == Title.DESIGNER or
                    position == Title.MEDICAL_DOCTOR)
        else:
            raise TypeError("position must be of type Position or str")
    