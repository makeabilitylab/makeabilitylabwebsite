from django.db import models
from django.dispatch import receiver
from django.db.models.signals import pre_delete, post_save, m2m_changed, post_delete
from django.core.files import File
import website.utils.fileutils as ml_fileutils

# For caching properties, see: https://docs.djangoproject.com/en/4.2/ref/utils/#django.utils.functional.cached_property
from django.utils.functional import cached_property 


import re
from datetime import date, datetime, timedelta

from image_cropping import ImageRatioField

from .position import Position

# Special character mappings
special_chars = {
    'ã': 'a', 'à': 'a', 'â': 'a',
    'é': 'e', 'è': 'e', 'ê': 'e',
    'ñ': 'n', 'ń': 'n',
    'ö': 'o', 'ô': 'o',
    'û': 'u', 'ü': 'u', 'ù': 'u'
}

class Person(models.Model):
    first_name = models.CharField(max_length=40)
    middle_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50)
    url_name = models.CharField(editable=False, max_length=50, default='placeholder')
    email = models.EmailField(blank=True, null=True)
    personal_website = models.URLField(blank=True, null=True)
    github = models.URLField(blank=True, null=True)
    twitter = models.URLField(blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    next_position = models.CharField(max_length=255, blank=True, null=True)
    next_position.help_text = "This is a field to track the next position held by alumni of the lab. This field stores text information about their position and the next field stores a url for that position."
    next_position_url = models.URLField(blank=True, null=True)

    # Note: the ImageField requires the pillow library, which can be installed using pip
    # pip3 install Pillow
    # We use the get_unique_path function because otherwise if two people use the same
    # filename (something generic like picture.jpg), one will overwrite the other.
    image = models.ImageField(blank=True, upload_to="person", max_length=255)

    # image_cropped = models.ImageField(editable=False)
    image.help_text = 'You must select "Save and continue editing" at the bottom of the page after uploading a new image for cropping.'

    easter_egg = models.ImageField(blank=True, null=True, upload_to="person", max_length=255)

    # LS: Added image cropping to fixed ratio
    # See https://github.com/jonasundderwolf/django-image-cropping
    # size is "width x height"
    # TODO: update with desired aspect ratio and maximum resolution
    cropping = ImageRatioField('image', '245x245', size_warning=True)
    easter_egg_crop = ImageRatioField('easter_egg', '245x245', size_warning=True)

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
            return Position.TITLE_ORDER_MAPPING[Position.UNKNOWN]

    @cached_property
    def get_current_department(self):
        """Returns current department for person. A cached property."""
        latest_position = self.get_latest_position
        if latest_position is not None:
            return latest_position.department
        else:
            return None

    get_current_title.short_description = "Department"

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
        # print(self.get_full_name() + " is active? " + str(self.is_current_member()) + " " +
        # str(self.is_current_collaborator()))
        return self.is_current_member() or self.is_current_collaborator()

    is_active.short_description = "Is Active?"

    @cached_property
    def get_total_time_in_role(self, role):
        """Returns the total time as in the specified role across all positions. A cached property."""
        totalTimeInRole = timedelta(0)
        for position in self.position_set.all():
            if position.role == role:
                totalTimeInRole += position.get_time_in_this_position()
        return totalTimeInRole

    get_total_time_in_role.short_description = "Total Time In Role"

    @cached_property
    def get_total_time_as_member(self):
        """Returns the total time as a member across all positions. A cached property."""
        return self.get_total_time_in_role(Position.MEMBER)

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
        
        # Check all previous positions
        for position in self.position_set.all():
            if position.is_member() is True:
                return True

        return False

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

    def get_earliest_position_in_role(self, role, contiguous_constraint=True):
        """Gets the earliest Position for this person in the given role

        :param:
            role: the role, see Position ROLE_CHOICES
            contiguous_constraint: if True, then we look only at continguous dates
        :return: the earliest Position for this person
        """
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
    def get_latest_position(self):
        """Gets the latest Position for the person or None if none exists. A cached property."""
        if self.position_set.exists() is False:
            return None
        else:
            return self.position_set.latest('start_date')
        
    @cached_property
    def get_start_date(self):
        """Returns the start date of current position. A cached property.
           Used in Admin Interface. See PersonAdmin in admin.py"""
        latest_position = self.get_latest_position
        if latest_position is not None:
            return latest_position.start_date
        else:
            return None

    get_start_date.short_description = "Start Date"  # This short description is used in the admin interface

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

        # Check if their headshot image is not set. If not, set to random star war image
        if not self.image:
            rand_star_wars_filename = ml_fileutils.get_path_to_random_starwars_image()
            rand_star_wars_image = File(open(rand_star_wars_filename, 'rb'))
            self.image = rand_star_wars_image

        # Check if their easter egg image is not set. If not, set to random star war image
        if self.easter_egg is None: 
            rand_star_wars_filename = ml_fileutils.get_path_to_random_starwars_image()
            rand_star_wars_image = File(open(rand_star_wars_filename, 'rb'))
            self.easter_egg = rand_star_wars_image

        super(Person, self).save(*args, **kwargs)

    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name_plural = 'People'


@receiver(pre_delete, sender=Person)
def person_delete(sender, instance, **kwargs):
    if instance.image:
        instance.image.delete(False)