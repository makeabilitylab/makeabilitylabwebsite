from django.db import models

from image_cropping import ImageRatioField

from datetime import date, datetime, timedelta

from .sponsor import Sponsor
from .project_umbrella import Project_umbrella
from .keyword import Keyword
from .publication import Publication
from .talk import Talk
from .video import Video


class Project(models.Model):
    name = models.CharField(max_length=255)

    # Short name is used for urls, and should be name.lower().replace(" ", "")
    short_name = models.CharField(max_length=255)
    short_name.help_text = "This should be the same as your name but lower case with no spaces. It is used in the url of the project"

    # Sponsors is currently a simple list of sponsors but could be updated to a many to many field if a sponsors model is desired.
    sponsors = models.ManyToManyField('Sponsor', blank=True, null=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    project_umbrellas = models.ManyToManyField('Project_umbrella', blank=True, null=True)

    # header_visual = models.ForeignKey(Project_header, blank=True, null=True)
    keywords = models.ManyToManyField(Keyword, blank=True, null=True)

    # pis = models.ManyToOneField(Person, blank=True, null=True)
    # TODO: consider switching gallery_image var name to thumbnail
    gallery_image = models.ImageField(upload_to='projects/images', blank=True, null=True, max_length=255)
    gallery_image.help_text = "This is the image which will show up on the project gallery page. It is not displayed anywhere else. You must select 'Save and continue editing' at the bottom of the page after uploading a new image for cropping. Please note that since we are using a responsive design with fixed height banners, your selected image may appear differently on various screens."

    # Copied from person model
    # LS: Added image cropping to fixed ratio
    # See https://github.com/jonasundderwolf/django-image-cropping
    # size is "width x height"
    # TODO: update with desired aspect ratio and maximum resolution
    cropping = ImageRatioField('gallery_image', '500x400', size_warning=True)

    about = models.TextField(null=True, blank=True)

    updated = models.DateField(auto_now=True)

    def get_pis(self):
        """Returns the PIs for the project (as a Person object)"""
        pis_queryset = self.project_role_set.filter(pi_member="PI")
        pis_list = [pi.person for pi in pis_queryset]
        print("queryset: ", pis_queryset)
        print(pis_list)
        return pis_list

    def get_co_pis(self):
        """Returns the PIs for ths project (as a list of Person objects)"""
        copis_queryset = self.project_role_set.filter(pi_member="Co-PI")
        copis_list = [copi.person for copi in copis_queryset]
        print(copis_list)
        return copis_list

    def has_award(self):
        """Returns true if one or more pubs have an award"""
        if self.publication_set.exists():
            # For filtering, see: https://stackoverflow.com/a/844572
            num_award_papers = self.publication_set.filter(award__isnull=False).exclude(award__exact='').count()
            return num_award_papers > 0
        else:
            return False

    def can_show_online(self):
        """Returns true if we can show this project on the webpage"""
        return self.has_thumbnail() and self.has_publication()

    def has_thumbnail(self):
        """Returns true if a project thumbnail has been set"""
        # From: https://stackoverflow.com/a/8850547
        return bool(self.gallery_image)

    def has_publication(self):
        """Returns True if the project has at least one publication"""
        return self.get_publication_count() > 0

    def get_most_recent_publication(self):
        """Returns the most recent publication for project"""
        if self.publication_set.exists():
            return self.publication_set.order_by('-date')[0]
        else:
            return None

    def has_artifact(self):
        """
        Returns true if project has at least one artifact (pub, talk, or video)
        """
        return self.get_most_recent_artifact() is not None

    def has_ended(self):
        """Returns true if the project has ended"""
        return self.end_date is not None and self.end_date < date.today()

    def get_most_recent_artifact_date(self):
        """
        Returns the most recent artifact date (if one exists); otherwise None
        :return: the most recent artifact date (if one exists); otherwise None
        """
        most_recent_artifact_tuple = self.get_most_recent_artifact()
        if most_recent_artifact_tuple is not None:
            return most_recent_artifact_tuple[0]
        else:
            return None

    get_most_recent_artifact_date.short_description = "Most Recent Artifact Date"

    def get_most_recent_artifact_type(self):
        """
        Returns either "Publication", "Talk", or "Video" or None
        :return: either "Publication", "Talk", or "Video" or None
        """
        most_recent_artifact_tuple = self.get_most_recent_artifact()
        if most_recent_artifact_tuple is not None:
            most_recent_artifact = most_recent_artifact_tuple[1]
            if type(most_recent_artifact) is Publication:
                return "Publication"
            elif type(most_recent_artifact) is Talk:
                return "Talk"
            elif type(most_recent_artifact) is Video:
                return "Video"
        else:
            return None

    get_most_recent_artifact_type.short_description = "Most Recent Artifact Type"

    def get_publication_count(self):
        """
        Returns the number of publications associated with this project
        :return: the number of publications associated with this project
        """
        return self.publication_set.count()

    get_publication_count.short_description = "Pubs"

    def get_video_count(self):
        """
        Returns the number of videos associated with this project
        :return: the number of videos associated with this project
        """
        return self.video_set.count()

    get_video_count.short_description = "Videos"

    def get_talk_count(self):
        """
        Returns the number of talks associated with this project
        :return: the number of talks associated with this project
        """
        return self.talk_set.count()

    get_talk_count.short_description = "Talks"

    def get_people_count(self):
        """
        Returns the number of people involved in the project
        :return:
        """
        project_roles = self.project_role_set.order_by('-start_date')

        # For more on this style of list iteration (called list comprehension)
        # See: https://docs.python.org/3/tutorial/datastructures.html#list-comprehensions
        #      https://www.python.org/dev/peps/pep-0202/
        people = set([project_role.person for project_role in project_roles])
        return len(people)

    get_people_count.short_description = "People"

    def get_current_member_count(self):
        """
        Returns the number of current members
        :return:
        """
        project_roles = self.project_role_set.order_by('-start_date')
        current_member_cnt = 0
        for project_role in project_roles:
            if project_role.is_active():
                current_member_cnt = current_member_cnt + 1
        return current_member_cnt

    get_current_member_count.short_description = "Current Members"

    def get_past_member_count(self):
        """
        Returns the number of current members
        :return:
        """

        # TODO: could likely turn all of this code into a single query?
        project_roles = self.project_role_set.order_by('-start_date')
        past_member_cnt = 0
        for project_role in project_roles:
            if project_role.is_active():
                past_member_cnt = past_member_cnt + 1
        return past_member_cnt

    get_past_member_count.short_description = "Past Members"

    def get_most_recent_artifact(self):
        """
        Returns the most recent artifact (publication, talk, or video) as tuple of (date, artifact)
        :return: the most recent artifact, a tuple of (date, artifact)
        """
        mostRecentArtifacts = []

        if self.publication_set.exists():
            mostRecentPub = self.publication_set.order_by('-date')[0]
            mostRecentArtifacts.append((mostRecentPub.date, mostRecentPub))

        if self.talk_set.exists():
            mostRecentTalk = self.talk_set.order_by('-date')[0]
            mostRecentArtifacts.append((mostRecentTalk.date, mostRecentTalk))

        if self.video_set.exists():
            mostRecentVideo = self.video_set.order_by('-date')[0]
            mostRecentArtifacts.append((mostRecentVideo.date, mostRecentVideo))

        if len(mostRecentArtifacts) > 0:
            mostRecentArtifacts = sorted(mostRecentArtifacts, key=lambda artifact: artifact[0], reverse=True)
            return mostRecentArtifacts[0][0], mostRecentArtifacts[0][1]
        else:
            return None

    get_most_recent_artifact.short_description = "Most Recent Artifact"


    def __str__(self):
        return self.name