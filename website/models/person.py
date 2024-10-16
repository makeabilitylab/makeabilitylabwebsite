from django.db import models
from django.dispatch import receiver
from django.db.models.signals import pre_delete, post_save, m2m_changed, post_delete
from website.models.publication import PubType
from website.models.position import Role, Title
from website.models.project_role import ProjectRole
from django.core.files import File
import website.utils.fileutils as ml_fileutils

from django.db.models import F, Q, Sum, ExpressionWrapper, fields
from django.utils import timezone
from django.db.models.functions import Coalesce

# For caching properties, see: https://docs.djangoproject.com/en/4.2/ref/utils/#django.utils.functional.cached_property
from django.utils.functional import cached_property 

from django.utils.safestring import mark_safe # for the html we use in help_text

import os # for joining paths
from uuid import uuid4 # for generating unique filenames

import re
from datetime import date, datetime, timedelta

from image_cropping import ImageRatioField

from .position import Position
from django.apps import apps # to solve circular import with importing Publications

import logging # for logging
import string # for punctuation

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

# Special character mappings
special_chars = {
    'ã': 'a', 'à': 'a', 'â': 'a',
    'é': 'e', 'è': 'e', 'ê': 'e',
    'ñ': 'n', 'ń': 'n',
    'ö': 'o', 'ô': 'o',
    'û': 'u', 'ü': 'u', 'ù': 'u'
}

PERSON_THUMBNAIL_SIZE = (245, 245)

def get_unique_filename_for_person(person, original_filename, append_str=None, force_unique=True):
    """Gets a unique filename with path for the person"""
    # get the extension of the uploaded file
    file_ext = os.path.splitext(original_filename)[1].lower()

    new_filename_without_ext = person.get_full_name(True).lower() # get full filename with middle name
    new_filename_without_ext = new_filename_without_ext.translate(str.maketrans('', '', string.punctuation)) # remove punctuation from filename
    new_filename_without_ext = new_filename_without_ext.replace(" ", "_") # replace spaces with underscores

    # Check if the append str should be added
    if append_str is not None:
        new_filename_without_ext += append_str

    new_filename_with_path = os.path.join(Person.UPLOAD_DIR, new_filename_without_ext + file_ext)

    # Check to see if we want to force unique filenames
    if force_unique:
        while os.path.exists(new_filename_with_path):
            _logger.debug(f"This filename with path exists {new_filename_with_path}, trying to generate a unique one")
            
            # The uuid4().hex generates a random UUID (Universally Unique Identifier), which is then appended to the filename. 
            # This makes the probability of generating a duplicate filename extremely low. 
            new_filename_with_path = os.path.join(Person.UPLOAD_DIR, new_filename_without_ext + uuid4().hex + file_ext)
            _logger.debug(f"Here's the new filename with path {new_filename_with_path}")
    
    _logger.debug(f"original_filename: {original_filename} new_filename_with_path: {new_filename_with_path}")
    return new_filename_with_path

def get_upload_to_for_person(person, original_filename, force_unique=True):
    """
    Constructs a new filename from the person’s name and the original file extension. This function is passed to the 
    upload_to parameter of the ImageField. When an image is uploaded, Django will call this function to determine the 
    name and path of the file to store on the filesystem.
    """
    return get_unique_filename_for_person(person, original_filename, None, force_unique)

def get_upload_to_for_person_easter_egg(person, original_filename, force_unique=True):
    """
    Constructs a new filename from the person’s name and the original file extension. This function is passed to the 
    upload_to parameter of the ImageField. When an image is uploaded, Django will call this function to determine the 
    name and path of the file to store on the filesystem.
    """

    append_str = "_easteregg"
    original_filename = original_filename.lower()
    if 'starwars' in original_filename:
        filename = os.path.basename(original_filename)
        filename_without_extension = os.path.splitext(filename)[0]
        append_str += "_" + "starwars" + "_" + filename_without_extension

    return get_unique_filename_for_person(person, original_filename, append_str, force_unique)

class Person(models.Model):
    UPLOAD_DIR = 'person/' # relative path

    @staticmethod  # use as decorator
    def get_thumbnail_size_as_str():
        return f"{PERSON_THUMBNAIL_SIZE[0]}x{PERSON_THUMBNAIL_SIZE[1]}"

    first_name = models.CharField(max_length=40)
    middle_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50)
    url_name = models.CharField(editable=False, max_length=50, default='placeholder')
    email = models.EmailField(blank=True, null=True)
    
    # Website links
    personal_website = models.URLField(blank=True, null=True)
    personal_website.help_text = 'Put the full url. For example, <a href="https://jonfroehlich.github.io/">https://jonfroehlich.github.io/</a>'
    github = models.URLField(blank=True, null=True)
    github.help_text = 'Again, put the full url. For example, <a href="https://github.com/jonfroehlich">https://github.com/jonfroehlich</a>'
    twitter = models.URLField(blank=True, null=True)
    threads = models.URLField(blank=True, null=True)
    mastodon = models.URLField(blank=True, null=True)
    linkedin = models.URLField(blank=True, null=True)
    
    # If a bio is not added, the member view page will auto-generate one
    bio = models.TextField(blank=True, null=True)
    bio.help_text = "You can use HTML markup here. If a bio is not added, the member view page will auto-generate one."
    bio_datetime_modified = models.DateField(null=True, blank=True)

    next_position = models.CharField(max_length=255, blank=True, null=True)
    next_position.help_text = "This is a field to track the next position held by alumni of the lab. This field stores text information about their position and the next field stores a url for that position."
    next_position_url = models.URLField(blank=True, null=True)

    # Note: the ImageField requires the pillow library
    # We use the get_unique_path function because otherwise if two people use the same
    # filename (something generic like picture.jpg), one will overwrite the other.
    image = models.ImageField(blank=True, upload_to=get_upload_to_for_person, max_length=255)
    image.help_text = 'You must select "Save and continue editing" at the bottom of the page after uploading a new image for cropping.'

    # We use the django-image-cropping ImageRatioField https://github.com/jonasundderwolf/django-image-cropping
    # that simply stores the boundaries of a cropped image. You must pass it the corresponding ImageField
    # and the desired size of the cropped image as arguments. The size passed in defines both the aspect ratio
    # and the minimum size for the final image
    cropping = ImageRatioField('image', get_thumbnail_size_as_str(), size_warning=True)

    # This is the hover image (aka easter egg)
    easter_egg = models.ImageField(blank=True, null=True, upload_to=get_upload_to_for_person_easter_egg, max_length=255)
    easter_egg.help_text = mark_safe("You do not have to set this field. It defaults to a Star Wars\
            Rebels LEGO character from <a href='https://github.com/makeabilitylab/makeabilitylabwebsite/tree/master/media/images/StarWarsFiguresFullSquare/Rebels'>here</a>\
            but you can use whatever you want. This image is shown on mouseover on the people.html page.")
    
    easter_egg_crop = ImageRatioField('easter_egg', get_thumbnail_size_as_str(), size_warning=True)
    easter_egg_crop.help_text = mark_safe("This image defaults to a Star Wars LEGO figure from\
        <a href='https://brickipedia.fandom.com/wiki/Star_Wars'>Brickipedia's Star War page</a>\
        but you can set it to anything you want and crop it appropriately here")

    def has_website_links(self):
        """Returns True if person has a personal website, github, or twitter, etc. False otherwise."""
        return self.personal_website or self.github or self.twitter

    @cached_property
    def is_graduated_phd_student(self):
        """Returns True if person is a graduated PhD student. False otherwise. A cached property."""
        return self.get_dissertation is not None

    @cached_property
    def get_dissertation(self):
        """Returns the Publication object for this person's dissertation. A cached property."""
        pubModel = apps.get_model('website', 'Publication')

        # Don't use a `get` query here because if there are no results that match the 
        # query, get() will raise a DoesNotExist exception
        # See: https://docs.djangoproject.com/en/4.2/topics/db/queries/#retrieving-a-single-object-with-get
        # return pubModel.objects.get(pub_venue_type=pubModel.PHD_DISSERTATION, authors=self)
        dissertation = pubModel.objects.filter(pub_venue_type=PubType.PHD_DISSERTATION, authors=self)
        if dissertation.exists():
            return dissertation[0]

    @cached_property
    def get_current_title(self):
        """Returns the title for person's current position. A cached property."""
        latest_position = self.get_latest_position
        if latest_position is not None:
            return latest_position.title
        else:
            return None

    get_current_title.short_description = "Title"


    @cached_property
    def get_current_title_index(self):
        """Returns the title index for person's current position. A cached property."""
        latest_position = self.get_latest_position
        if latest_position is not None:
            return latest_position.get_title_index()
        else:
            return Position.TITLE_ORDER_MAPPING[Title.UNKNOWN]

    @cached_property
    def get_current_department(self):
        """Returns current department for person. A cached property."""
        latest_position = self.get_latest_position
        if latest_position is not None:
            return latest_position.department
        else:
            return None

    get_current_department.short_description = "Department"

    @cached_property
    def get_current_school(self):
        """Returns current school for person. A cached property."""
        latest_position = self.get_latest_position
        if latest_position is not None:
            return latest_position.school
        else:
            return None

    get_current_school.short_description = "School"

    @cached_property
    def get_current_role(self):
        """Returns current role for person. A cached property."""
        latest_position = self.get_latest_position
        if latest_position is not None:
            return latest_position.role
        else:
            return None

    get_current_role.short_description = "Role"

    def get_total_time_on_project(self, project):
        """
        Returns the total time as a timedelta this person has worked on the given project.
        If the end_date is None, the current date/time is used.
        """
        print(f"person {self}, project {project}")
        # Get the roles this person has had on the given project
        roles = ProjectRole.objects.filter(person=self, project=project)

        print(f"person {self}, roles {roles}")
        # If there are no roles, return a timedelta of zero duration
        if not roles.exists():
            return timedelta()

        # Calculate the total time worked as the sum of (end_date - start_date) for each role
        # If end_date is None, use the current date/time
        # total_time_worked = roles.annotate(
        #     time_worked=ExpressionWrapper(
        #         (F('end_date') if F('end_date') is not None else timezone.now()) - F('start_date'),
        #         output_field=fields.DurationField()
        #     )
        # ).aggregate(total_time=Sum('time_worked'))['total_time']

        # Calculate the total time worked as the sum of (end_date - start_date) for each role
        # If end_date is None, use the current date/time
        total_time_worked = roles.annotate(
            time_worked=ExpressionWrapper(
                Coalesce(F('end_date'), timezone.now()) - F('start_date'),
                output_field=fields.DurationField()
            )
        ).aggregate(total_time=Sum('time_worked'))['total_time']

        print(f"person {self}, total_time_worked", total_time_worked)

        # Returns a timedelta object, which is part of Python’s datetime module and it represents
        # a duration, or the difference between two dates or times.
        return total_time_worked

    @cached_property
    def get_time_in_current_position(self):
        """Returns time in current position (as a timedelta object). A cached property."""
        latest_position = self.get_latest_position
        if latest_position is not None:
            return latest_position.get_time_in_this_position()
        else:
            return None

    get_time_in_current_position.short_description = "Time in Current Position"

    @cached_property
    def is_professor(self):
        """Returns true if a professor in current position. A cached property."""
        latest_position = self.get_latest_position
        if latest_position is not None:
            return latest_position.is_professor()
        else:
            return False

    @cached_property
    def is_grad_student(self):
        """Returns true if a grad student in current position. A cached property."""
        latest_position = self.get_latest_position
        if latest_position is not None:
            return latest_position.is_grad_student()
        else:
            return False

    @cached_property
    def is_active(self):
        """Returns True is person is current member of lab or current collaborator. A cached property."""
        return self.is_current_member or self.is_current_collaborator

    is_active.short_description = "Is Active?"

    @cached_property
    def has_started(self):
        """Returns True if person has started in the lab. False otherwise."""
        return self.get_latest_position.has_started()

    def get_total_time_in_role(self, role):
        """Returns the total time as in the specified role across all positions as a DurationField"""
        duration = ExpressionWrapper(Coalesce(F('end_date'), date.today()) - F('start_date'), output_field=fields.DurationField())
        total_time_in_role = self.position_set.filter(role=role).aggregate(total=Sum(duration))['total']
        return total_time_in_role

    get_total_time_in_role.short_description = "Total Time In Role"

    def get_total_time_in_lab(self):
        """Returns the total time in the lab across all roles as a DurationField"""
        duration = ExpressionWrapper(Coalesce(F('end_date'), date.today()) - F('start_date'), output_field=fields.DurationField())
        total_time_in_lab = self.position_set.aggregate(total=Sum(duration))['total']
        return total_time_in_lab

    get_total_time_in_lab.short_description = "Total Time In Lab"

    @cached_property
    def get_total_time_as_member(self):
        """Returns the total time as a member across all positions. A cached property."""
        return self.get_total_time_in_role(Role.MEMBER)

    get_total_time_as_member.short_description = "Total Time As Member"

    @cached_property
    def is_current_member(self):
        """Returns True if person is current member of the lab. False otherwise"""
        latest_position = self.get_latest_position
        if latest_position is not None:
            return latest_position.is_current_member()
        else:
            return False

    @cached_property
    def is_alumni_member(self):
        """
        Returns True if person is an alumni member of the lab. False otherwise. 
        Note that some members of our lab have been alumni and are also current members
        That is, they may have started as high school students then left the lab
        then returned as a grad student. A cached property."""
        
        # we use Django’s Q objects to construct a complex query. We check if there exists any position 
        # where the role was Position.MEMBER and the end date is less than the current time (i.e., in the past). 
        # The exists() method returns True if such a position exists, and False otherwise.
        return self.position_set.filter(Q(role=Role.MEMBER) & Q(end_date__lt=timezone.now())).exists()

    @cached_property
    def is_current_collaborator(self):
        """Returns True if person is current collaborator of the lab. False otherwise. A cached property."""
        latest_position = self.get_latest_position
        if latest_position is not None:
            return latest_position.is_current_collaborator()
        else:
            return False

    @cached_property
    def is_past_collaborator(self):
        """Returns True if person is a past collaborator of the lab. False otherwise. A cached property."""
        latest_position = self.get_latest_position
        if latest_position is not None:
            return latest_position.is_past_collaborator()
        else:
            return False

    @cached_property
    def get_latest_phd_student_position(self):
        """Returns the latest position for this person that is a PhD student. A cached property."""
        return self.get_latest_position_in_title(Title.PHD_STUDENT)

    def get_latest_position_in_title(self, title):
        """Returns the latest position in the specified role. A cached property."""
        return self.position_set.filter(title=title).latest('start_date')

    def get_earliest_position_in_role(self, role, contiguous_constraint=True):
        """Gets the earliest Position for this person in the given role

        :param:
            role: the role, see Position ROLE_CHOICES
            contiguous_constraint: if True, then we look only at continguous dates
        :return: the earliest Position for this person
        """

        # Note: given the complicated logic with the continguous_constraint, we don't use 
        # Django's ORM to do this query. Instead, we do it manually, which is slower but
        # the code is more readable (and I struggled to come up with an ORM equivalent)
        if not contiguous_constraint:
            # The result of a QuerySet is a QuerySet so you can chain them together...
            return self.position_set.filter(role=role).earliest('start_date')
        else:
            next_position = None
            for cur_position in self.position_set.filter(role=role).order_by('-start_date'):
                # we are going backwards in time. as soon as there is a gap greater than
                # max_time_gap, we stop
                max_time_gap = timedelta(weeks=1)
                print(self.get_full_name(), cur_position)
                if next_position is None:
                    next_position = cur_position
                elif (next_position.start_date - cur_position.end_date) <= max_time_gap:
                    time_gap = (next_position.start_date - cur_position.end_date)
                    # print("Met minimum time gap: gap= {} max_gap={}".format(time_gap, max_time_gap))
                    next_position = cur_position
                else:
                    time_gap = (next_position.start_date - cur_position.end_date)
                    # print("Exceeded minimum time gap: gap= {} max_gap={}".format(time_gap, max_time_gap))
                    break

            return next_position

    @cached_property
    def get_earliest_position(self):
        """Gets the earliest Position for the person or None if none exists. A cached property."""
        if self.position_set.exists() is False:
            return None
        else:
            return self.position_set.earliest('start_date')
    
    @cached_property
    def get_latest_position(self):
        """Gets the latest Position for the person or None if none exists. A cached property."""
        if self.position_set.exists() is False:
            return None
        else:
            return self.position_set.latest('start_date')
        
    @cached_property
    def get_start_date(self):
        """Returns the overall start date of person. A cached property.
           Used in Admin Interface. See PersonAdmin in admin.py"""
        earliest_position = self.get_earliest_position
        if earliest_position is not None:
            return earliest_position.start_date
        else:
            return None

    get_start_date.short_description = "Lab Start Date"  # This short description is used in the admin interface

    @cached_property
    def get_cur_pos_start_date(self):
        """Returns the start date of current position. A cached property.
           Used in Admin Interface. See PersonAdmin in admin.py"""
        latest_position = self.get_latest_position
        if latest_position is not None:
            return latest_position.start_date
        else:
            return None

    get_cur_pos_start_date.short_description = "Cur Pos Start"  # This short description is used in the admin interface

    @cached_property
    def get_end_date(self):
        """Returns the end date of current position. A cached property.
        Used in Admin Interface. See PersonAdmin in admin.py"""
        latest_position = self.get_latest_position
        if latest_position is not None:
            return latest_position.end_date
        else:
            return None

    get_end_date.short_description = "End Date"  # This short description is used in the admin interface

    def get_full_name(self, include_middle=True):
        """
        Gets this person's full name as a string.
        :param include_middle: If true, includes the middle name. Defaults to True.
        :return: the person's full name as a string
        """
        if self.middle_name and include_middle:
            return u"{0} {1} {2}".format(self.first_name, self.middle_name, self.last_name)
        else:
            return u"{0} {1}".format(self.first_name, self.last_name)

    get_full_name.short_description = "Full Name"
    get_full_name.admin_order_field = 'first_name'  # Allows column order sorting based on full name

    def get_citation_name(self, include_middle=True, full_name=True):
        """Returns name formatted for a citation"""
        citation_name = self.last_name

        if full_name:
            citation_name += ", " + self.first_name
        else:
            citation_name += ", " + self.first_name.upper()[0] + "."

        if self.middle_name and include_middle:
            if full_name:
                citation_name += " " + self.middle_name
            else:
                citation_name += " " + self.middle_name.upper()[0] + "."

        return citation_name

    def get_url_name(self):
        """Gets the URL name for this person. Format: firstlast"""
        return self.url_name
    
    @cached_property
    def get_project_count(self):
        """Gets the number of projects for this person. A cached property."""
        return self.projectrole_set.count()
    
    get_project_count.short_description = "Projects"

    @cached_property
    def get_pub_count(self):
        """Gets the number of publications for this person. A cached property."""
        return self.publication_set.count()
    
    get_pub_count.short_description = "Pubs"
    
    @cached_property
    def get_talk_count(self):
        """Gets the number of talks for this person. A cached property."""
        return self.talk_set.count()
    
    get_talk_count.short_description = "Talks"

    @cached_property
    def get_projects(self):
        """
        Gets a set of all the projects this person is involved in ordered by most recent start date first
        Note: a cached property
        :return: a set of all the projects this person is involved in ordered by most recent start date first
        """
        project_roles = self.projectrole_set.order_by('-start_date')

        # For more on this style of list iteration (called list comprehension)
        # See: https://docs.python.org/3/tutorial/datastructures.html#list-comprehensions
        #      https://www.python.org/dev/peps/pep-0202/
        projects = set([project_role.project for project_role in project_roles])
        return projects

    def get_mentees(self, randomize=False):
        """
        Returns a list of all students this person has mentored
        """
        grad_mentors = Position.objects.filter(grad_mentor=self).values('person')
        mentees = Person.objects.filter(id__in=grad_mentors)
        
        # Randomize the order of the mentees if randomize is True
        if randomize:
            mentees = mentees.order_by('?')
        
        return mentees

    def get_grad_mentors(self):
        """
        Retrieve a list of grad mentors for the current person instance.

        This method filters the Person objects to find those who are listed as
        grad mentors for the current person in the Position model. It ensures
        that each mentor is listed only once using the distinct() method.

        Returns:
            QuerySet: A QuerySet of Person objects who are grad mentors for the current person.
        """
        positions = Position.objects.filter(person=self)
        grad_mentors = positions.values('grad_mentor')
        return Person.objects.filter(id__in=grad_mentors)

    def get_projects_sorted_by_contrib(self, filter_out_projs_with_zero_pubs=True):
        """Returns a set of all projects this person is involved in ordered by number of pubs"""
        map_project_name_to_tuple = dict() # tuple is (count, most_recent_pub_date, project)
        #publications = self.publication_set.order_by('-date')

        # Go through all the projects by this person and track how much
        # they've contributed to each one (via publication)
        #print("******{}*******".format(self.get_full_name()))
        for pub in self.publication_set.all():
            for proj in pub.projects.all():
                #print("pub", pub, "proj", proj)
                if proj.name not in map_project_name_to_tuple:
                    most_recent_date = proj.start_date
                    if most_recent_date is None:
                        most_recent_date = pub.date
                    if most_recent_date is None:
                        most_recent_date = datetime.date(2012, 1, 1) # when the lab was founded

                    map_project_name_to_tuple[proj.name] = (0, most_recent_date, proj)

                tuple_cnt_proj = map_project_name_to_tuple[proj.name]
                most_recent_date = tuple_cnt_proj[1]
                if pub.date is not None and pub.date > most_recent_date:
                    most_recent_date = pub.date

                map_project_name_to_tuple[proj.name] = (tuple_cnt_proj[0] + 1, # pub cnt
                                                        most_recent_date,      # most recent pub date
                                                        tuple_cnt_proj[2])     # project

        list_tuples = list([tuple_cnt_proj for tuple_cnt_proj in map_project_name_to_tuple.values()])
        list_tuples_sorted = sorted(list_tuples, key=lambda t: (t[0], t[1]), reverse=True)

        #print("list_tuples_sorted", list_tuples_sorted)

        ordered_projects = []
        if len(list_tuples_sorted) > 0:
            list_cnts, list_dates, ordered_projects = zip(*list_tuples_sorted)

        if len(ordered_projects) <= 0 and not filter_out_projs_with_zero_pubs:
            # if a person hasn't published but is still on projects
            # default to this
            ordered_projects = self.get_projects()

        return ordered_projects


    def __str__(self):
        return self.get_full_name()

    def save(self, *args, **kwargs):
        
        # First, automatically set the url_name field
        # Substitute any common special characters. I haven't found a better automatic way to do
        # this, so we are manually mapping 'common' special characters.
        url_name_cleaned = (self.first_name + self.last_name).lower()
        for c in url_name_cleaned:
            if bool(re.search('[^a-zA-Z]', c)) and c in special_chars:
                url_name_cleaned = url_name_cleaned.replace(c, special_chars.get(c))

        # Finally, clean remaining characters (EX: dashes, periods).
        url_name_cleaned = re.sub('[^a-zA-Z]', '', url_name_cleaned)
        self.url_name = url_name_cleaned

        # Next, automatically set the bio_date_modified field
        if self.pk is not None: # checks if this is an existing object
            orig = Person.objects.get(pk=self.pk)
            if orig.bio != self.bio:
                self.bio_datetime_modified = timezone.now().date()
        else:
            self.bio_datetime_modified = timezone.now().date()

        # Check if their headshot image is not set. If not, set to random star war image
        if not self.image:
            _logger.debug(f"{self.get_full_name()} has NO image set. Setting to random star wars image")
            rand_star_wars_filename = ml_fileutils.get_path_to_random_starwars_image()
            rand_star_wars_image = File(open(rand_star_wars_filename, 'rb'))
            self.image = rand_star_wars_image
            _logger.debug(f"{self.get_full_name()}'s image has been set to {rand_star_wars_filename} with image: {self.image}")
        else:
            _logger.debug(f"{self.get_full_name()} has the image: {self.image} with cropping: {self.cropping}")

        # Check if their easter egg image is not set. If not, set to random star war image
        if not self.easter_egg: 
            _logger.debug(f"{self.get_full_name()} has no hover (easter egg) image set. Setting to random star wars image")
            rand_star_wars_filename = ml_fileutils.get_path_to_random_starwars_image()
            rand_star_wars_image = File(open(rand_star_wars_filename, 'rb'))
            self.easter_egg = rand_star_wars_image
            _logger.debug(f"{self.get_full_name()}'s hover image has been set to {rand_star_wars_filename} with image: {self.easter_egg}")
        else:
            _logger.debug(f"{self.get_full_name()} has the hover (easter egg) image: {self.easter_egg} with cropping: {self.easter_egg_crop}")

        super(Person, self).save(*args, **kwargs)


    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name_plural = 'People'


@receiver(pre_delete, sender=Person)
def person_delete(sender, instance, **kwargs):
    if instance.image:
        instance.image.delete(False)