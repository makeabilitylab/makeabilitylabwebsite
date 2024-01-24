from django.db import models
from django.db.models import Max, Min
from django.db.models import F, ExpressionWrapper, fields, Sum

from image_cropping import ImageRatioField

from datetime import date, datetime, timedelta

from .sponsor import Sponsor
from .project_umbrella import ProjectUmbrella
from .project_role import ProjectRole
from .project_role import LeadProjectRoleTypes
from .keyword import Keyword
from .publication import Publication
from .talk import Talk
from .video import Video
from .person import Person

import logging # for logging

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

import os

PROJECT_THUMBNAIL_SIZE = (500, 300) # 15 : 9 aspect ratio

class Project(models.Model):
    UPLOAD_DIR = 'projects/' # relative path
    IMAGE_DIR = os.path.join(UPLOAD_DIR, 'images/') # relative path

    @staticmethod  # use as decorator
    def get_thumbnail_size_as_str():
        return f"{PROJECT_THUMBNAIL_SIZE[0]}x{PROJECT_THUMBNAIL_SIZE[1]}"
    
    name = models.CharField(max_length=255)

    # Short name is used for urls, and should be name.lower().replace(" ", "")
    short_name = models.CharField(max_length=255)
    short_name.help_text = "This should be the same as name but lower case with no spaces. It is used in the url of the project"

    # Sponsors is currently a simple list of sponsors but could be updated to a many to many field if a sponsors model is desired.
    sponsors = models.ManyToManyField('Sponsor', blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    project_umbrellas = models.ManyToManyField('ProjectUmbrella', blank=True)
    featured_video = models.ForeignKey('Video', blank=True, null=True, on_delete=models.SET_NULL, related_name='related_project')
    featured_code_repo_url = models.URLField(blank=True, null=True)
    keywords = models.ManyToManyField(Keyword, blank=True)

    # pis = models.ManyToOneField(Person, blank=True, null=True)
    # TODO: consider switching gallery_image var name to thumbnail
    gallery_image = models.ImageField(upload_to=IMAGE_DIR, blank=True, null=True, max_length=255)
    gallery_image.help_text = "This is the image which will show up on the project gallery page.\
                               It is not displayed anywhere else. You must select 'Save and continue editing' at the\
                               bottom of the page after uploading a new image for cropping."
    thumbnail_alt_text = models.CharField(max_length=1024, blank=True, null=True)

    # We use the django-image-cropping ImageRatioField https://github.com/jonasundderwolf/django-image-cropping
    # that simply stores the boundaries of a cropped image. You must pass it the corresponding ImageField
    # and the desired size of the cropped image as arguments. The size passed in defines both the aspect ratio
    # and the minimum size for the final image
    cropping = ImageRatioField('gallery_image', get_thumbnail_size_as_str(), size_warning=True)

    about = models.TextField(null=True, blank=True)
    about.help_text = "Keep the word count to roughly 150-300 words. This is an HTML-compatible field. You can use HTML tags to format the text.\
                       For example, you can use <b>bold</b>, <i>italics</i>, <a href='https://makeabilitylab.cs.washington.edu'>links</a>"

    updated = models.DateField(auto_now=True)

    def save(self, *args, **kwargs):
        """
        This method overrides the default save method for the Project model.

        When a Project instance is saved, we check if the project's end_date has been set. 
        If it has, we iterate over all related ProjectRole instances where end_date is null
        and automatically set these end dates either to the Project end date or the person's
        lab departure date, whichever is earlier.
        """
        _logger.debug("Running Project.save() method...")
        super(Project, self).save(*args, **kwargs)  # Save the Project instance first

        if self.end_date:
            # Get ProjectRoles related to the Project that have a null end_date
            project_roles_to_close = ProjectRole.objects.filter(project=self, end_date__isnull=True)
            
            # Log and update the ProjectRoles that will be automatically closed
            for project_role in project_roles_to_close:
                person = project_role.person

                # We need to check if a person has left the lab. If they have, we need to check
                # to see if their lab departure date is before the project end date. If it is,
                # we need to use the lab departure date as the project role end date.
                if not person.is_active:
                    # Get the latest end_date among the person's positions
                    latest_position = person.get_latest_position
                    if latest_position and latest_position.end_date:
                        # Use the earlier of the project's end_date and the person's leaving date
                        end_date = min(self.end_date, latest_position.end_date)
                    else:
                        end_date = self.end_date
                else:
                    end_date = self.end_date

                _logger.info(f"Automatically closing ProjectRole: {project_role} for Person: {person} with end_date: {end_date}")
                
                # Update end_date of the ProjectRole
                project_role.end_date = end_date
                project_role.save()

    def get_featured_video(self):
        """
        This function returns the Project's video if it exists. 
        If the Project's video is null, it finds the most recent publication with a video and returns that.
        If no such publication exists, it returns None.

        Returns:
            Video: The video of the Project or the most recent publication with a video. None if no such video exists.
        """
        if self.featured_video is not None:
            return self.featured_video
        else:
            # Check for a project video
            recent_project_video = self.videos.order_by('-date').first()
            if recent_project_video is not None:
                return recent_project_video
    
            # Get the most recent publication asscoaited with this project with a video
            recent_publication_with_video = (Publication.objects
                                             .filter(video__isnull=False, projects=self)
                                             .order_by('-date').first())
            if recent_publication_with_video:
                return recent_publication_with_video.video
            else:
                return None

    def get_featured_code_repo_url(self):
        """
        This function returns the Project's code repository URL if it exists. 
        If the Project's code repository URL is null, it finds the most recent publication with a 
        code repository URL and returns that. If no such publication exists, it returns None.

        Returns:
            model.URLField: The code repository URL of the Project or the most recent publication 
                            with a code repository URL. None if no such URL exists.
        """
        if self.featured_code_repo_url is not None:
            return self.featured_code_repo_url
        else:
            # Get the most recent publication with a code repository URL
            recent_publication_with_code_repo_url = (Publication.objects
                                                     .filter(code_repo_url__isnull=False, projects=self)
                                                     .order_by('-date').first())
            if recent_publication_with_code_repo_url:
                return recent_publication_with_code_repo_url.code_repo_url
            else:
                return None

    def get_related_projects(self, match_all_umbrellas=False):
        """
        Gets all projects that share project umbrellas with this project.
        
        If match_all_umbrellas is True, it returns projects that share exactly the same project umbrellas.
        If match_all_umbrellas is False, it returns projects that share at least one project umbrella.
        
        Args:
            match_all_umbrellas (bool): Whether to match all project umbrellas or just one. Defaults to False.
        
        Returns:
            QuerySet: A QuerySet of Project instances that match the criteria.
        """
        if match_all_umbrellas:
            # If we want to match all project umbrellas,
            # we first annotate each project with the count of matching project umbrellas.
            # Then we filter the projects where the count of matching project umbrellas is equal to the count of project umbrellas in the current project.
            return (Project.objects
                    .annotate(matching_count=models.Count('project_umbrellas', filter=models.Q(project_umbrellas__in=self.project_umbrellas.all())))
                    .filter(matching_count=self.project_umbrellas.count())
                    .exclude(id=self.id)  # Exclude the current project from the results
                    .order_by('-start_date')  # Order the results by start_date in descending order
                    .distinct())  # Ensure each project is returned only once
        else:
            # If we want to match at least one project umbrella,
            # we simply filter the projects that have any of the same project umbrellas as the current project.
            return (Project.objects
                    .filter(project_umbrellas__in=self.project_umbrellas.all())
                    .exclude(id=self.id)  # Exclude the current project from the results
                    .order_by('-start_date')  # Order the results by start_date in descending order
                    .distinct())  # Ensure each project is returned only once

    
    def get_thumbnail_alt_text(self):
        if not self.thumbnail_alt_text:
            return "This is the thumbnail image for the project " + self.name
        else:
            return self.thumbnail_alt_text

    def get_pis(self):
        """Returns the PIs for the project (as a Person object)"""
        pis_queryset = (self.projectrole_set
                          .filter(pi_member=LeadProjectRoleTypes.PI)
                          .values_list('person', flat=True))
        return pis_queryset

    def get_co_pis(self):
        """Returns the Co-PIs for this project (as a QuerySet of Person objects)"""
        copis_queryset = (self.projectrole_set
                          .filter(pi_member=LeadProjectRoleTypes.CO_PI)
                          .values_list('person', flat=True))
        return copis_queryset

    def has_award(self):
        """
        Returns true if one or more publications have an award.

        Returns:
            bool: True if one or more publications have an award, False otherwise.
        """
        # Check if any publication has an award (not null and not an empty string)
        return self.publication_set.filter(award__isnull=False).exclude(award__exact='').exists()

    def can_show_online(self):
        """Returns true if we can show this project on the webpage"""
        return self.has_thumbnail() and self.has_publication()

    def has_thumbnail(self):
        """Returns true if a project thumbnail has been set"""
        # From: https://stackoverflow.com/a/8850547
        return bool(self.gallery_image)

    def has_publication(self):
        """
        Returns True if the project has at least one publication.

        Returns:
            bool: True if the project has at least one publication, False otherwise.
        """
        return self.publication_set.exists()

    def get_most_recent_publication(self):
        """
        Returns the most recent publication for the project.

        Returns:
            Publication: The most recent publication if it exists, None otherwise.
        """
        return self.publication_set.order_by('-date').first()


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
        return self.videos.count()

    get_video_count.short_description = "Videos"

    def get_banner_count(self):
        """
        Returns the number of banners associated with this project
        """
        return self.banner_set.count()
    
    get_banner_count.short_description = "Banners"

    def get_talk_count(self):
        """
        Returns the number of talks associated with this project
        :return: the number of talks associated with this project
        """
        return self.talk_set.count()

    get_talk_count.short_description = "Talks"

    def get_most_recent_roles(self):
        """
        Returns the most recent ProjectRole for each person that has worked on the project
        :return: QuerySet of ProjectRole instances
        """
        # Annotate each person with the date of their most recent role
        people = Person.objects.annotate(most_recent_role_date=Max('projectrole__start_date'))

        # Get the ProjectRoles that match the most recent role date for each person
        most_recent_roles = ProjectRole.objects.filter(
            person__in=people,
            start_date__in=[person.most_recent_role_date for person in people]
        )

        return most_recent_roles

    def get_people(self, sorted_by="time_on_project"):
        """
        Returns a QuerySet of all people who have worked on the project
        :return: QuerySet of Person instances
        """
        if sorted_by == "time_on_project":
            # Calculate time_worked as the difference between end_date and start_date
            # If end_date is None, use the current date as the end date
            time_worked = ExpressionWrapper(
                (F('projectrole__end_date') if F('projectrole__end_date') is not None else timezone.now()) - F('projectrole__start_date'),
                output_field=fields.DurationField()
            )
            return Person.objects.filter(projectrole__project=self).annotate(
                total_time_worked=Sum(time_worked)
            ).order_by('-total_time_worked').distinct()
        elif sorted_by == "start_date":
            # Sort by earliest start date
            return Person.objects.filter(projectrole__project=self).annotate(
                earliest_start_date=Min('projectrole__start_date')
            ).order_by('earliest_start_date').distinct()
        elif sorted_by == "alphabetical":
            # Sort by last name, then first name
            return Person.objects.filter(projectrole__project=self).order_by('last_name', 'first_name').distinct()
        else:
            return Person.objects.filter(projectrole__project=self).distinct()
    
    def get_contributors(self):
        """
        Returns a QuerySet of all people who have ProjectRoles associated with this project
        and who are listed as co-authors on any publications associated with this project.
      
        """
        # Get all people who have roles in this project
        role_people = ProjectRole.objects.filter(project=self).values_list('person', flat=True).distinct()

        # Get all authors from publications associated with this project
        publication_people = Publication.objects.filter(projects=self).values_list('authors', flat=True).distinct()

        # Combine the two querysets
        all_people = role_people.union(publication_people)

        return all_people

    def get_contributor_count(self):
        """
        Returns the total number of people with ProjectRoles associated with this project
        and who are listed as co-authors on any publications associated with this project.
        It should always be >= the number of people returned by get_people_count()
        """
        return self.get_contributors().count()

    get_contributor_count.short_description = "Contributors"

    def get_people_count(self):
        """
        Returns the number of people involved in the project
        """
        return self.projectrole_set.values('person').distinct().count()

    get_people_count.short_description = "Num People"

    def get_current_member_count(self):
        """
        Returns the number of current members
        """
        # project_roles = self.projectrole_set.order_by('-start_date')
        # current_member_cnt = 0
        # for project_role in project_roles:
        #     if project_role.is_active():
        #         current_member_cnt = current_member_cnt + 1
        # return current_member_cnt
        self.projectrole_set.filter(end_date__isnull=True).values('person').distinct().count()

    get_current_member_count.short_description = "Num Current Members"

    def get_past_member_count(self):
        """
        Returns the number of past members
        """
        return self.projectrole_set.filter(end_date__isnull=False).values('person').distinct().count()

    get_past_member_count.short_description = "Num Past Members"

    def get_most_recent_artifact(self):
        """
        Returns the most recent artifact (publication, talk, or video) as tuple of (date, artifact)
        :return: the most recent artifact, a tuple of (date, artifact)
        """
        mostRecentArtifacts = []

        if self.publication_set.exists():
            mostRecentPub = self.publication_set.latest('date')
            mostRecentArtifacts.append((mostRecentPub.date, mostRecentPub))

        if self.talk_set.exists():
            mostRecentTalk = self.talk_set.latest('date')
            mostRecentArtifacts.append((mostRecentTalk.date, mostRecentTalk))

        if self.videos.exists():
            mostRecentVideo = self.videos.latest('date')
            mostRecentArtifacts.append((mostRecentVideo.date, mostRecentVideo))

        if len(mostRecentArtifacts) > 0:
            return max(mostRecentArtifacts, key=lambda artifact: artifact[0])
        else:
            return None

    get_most_recent_artifact.short_description = "Most Recent Artifact"


    def get_project_dates_str(self):
        """
        Returns a string representation of the project's start and end dates.
        If the start and end dates are in the same year, it returns that year.
        If the end date is None, it returns a string in the format 'start_year–Present'.
        Otherwise, it returns a string in the format 'start_year–end_year'.
        """
        # If end_date is None, return 'start_year–Present'
        if self.end_date is None:
            return f"{self.start_date.year}–Present"

        # If start_date and end_date are in the same year, return that year
        if self.start_date.year == self.end_date.year:
            return str(self.start_date.year)

        # Otherwise, return 'start_year–end_year'
        return f"{self.start_date.year}–{self.end_date.year}"


    def __str__(self):
        return self.name