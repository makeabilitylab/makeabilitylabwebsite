import os
from website.models import Artifact
from django.db import models

# Django’s built-in Choices class: Django 3.0 introduced a Choices class with two subclasses: 
# IntegerChoices and TextChoices. These extend Python’s Enum types with extra constraints 
# and functionality to make them suitable for Field.choices1. 
class TalkType(models.TextChoices):
    """The talk type choices"""
    INVITED_TALK = "Invited Talk"
    CONFERENCE_TALK = "Conference Talk"
    MS_DEFENSE = "MS Defense"
    PHD_DEFENSE = "PhD Defense"
    GUEST_LECTURE = "Guest Lecture"
    QUALS_TALK = "Quals Talk"
    KEYNOTE_TALK = "Keynote Talk"

class Talk(Artifact):
    """
    The Talk class inherits from the Artifact class and represents a talk or presentation.
    It includes fields for the talk type, slideshare URL, video, and upload directories.
    """
    UPLOAD_DIR = 'talks/'
    THUMBNAIL_DIR = os.path.join(UPLOAD_DIR, 'images/')

    slideshare_url = models.URLField(blank=True, null=True)
    slideshare_url.help_text = "Slideshare is no longer a popular way of sharing talks"

    # add in video field to address https://github.com/jonfroehlich/makeabilitylabwebsite/issues/539
    video = models.ForeignKey('Video', blank=True, null=True, on_delete=models.DO_NOTHING)
    video.help_text = "If there is a video recording of the talk, add it here."

    talk_type = models.CharField(max_length=50, choices=TalkType.choices, null=True)
    talk_type.help_text = "If this is a conference talk (e.g., for CHI, ASSETS, UIST, IMWUT), please select 'Conference Talk'"

    def get_upload_dir(self, filename):
        """Gets the upload directory for this artifact. This is required by the parent class."""
        return os.path.join(self.UPLOAD_DIR, filename)

    def get_upload_thumbnail_dir(self, filename):
        """Gets the upload thumbnail directory for this artifact. This is required by the parent class."""
        return os.path.join(self.THUMBNAIL_DIR, filename)
    
    def get_speakers_as_csv(self):
        """Gets the list of speakers as a csv string"""
        return ', '.join(speaker.get_full_name() for speaker in self.authors.all())

    get_speakers_as_csv.short_description = 'Speaker List'