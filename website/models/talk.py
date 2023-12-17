import os
from website.models import Artifact
from django.db import models

# Django’s built-in Choices class: Django 3.0 introduced a Choices class with two subclasses: 
# IntegerChoices and TextChoices. These extend Python’s Enum types with extra constraints 
# and functionality to make them suitable for Field.choices1. 
class TalkType(models.TextChoices):
    INVITED_TALK = "Invited Talk"
    CONFERENCE_TALK = "Conference Talk"
    MS_DEFENSE = "MS Defense"
    PHD_DEFENSE = "PhD Defense"
    GUEST_LECTURE = "Guest Lecture"
    QUALS_TALK = "Quals Talk"
    KEYNOTE_TALK = "Keynote Talk"

class Talk(Artifact):
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
        return os.path.join(self.UPLOAD_DIR, filename)

    def get_upload_thumbnail_dir(self, filename):
        return os.path.join(self.THUMBNAIL_DIR, filename)
    
    def get_person(self):
        """Gets the "first author" (or speaker in this case) for the talk"""
        return self.authors.all()[0]
    
    def get_first_speaker_last_name(self):
        speakers = self.authors.all()
        if speakers.exists():
            return speakers.first().last_name
        else:
            return None

    def get_speakers_as_csv(self):
        """Gets the list of speakers as a csv string"""
        # iterate through all of the speakers and return the csv
        is_first_speaker = True
        list_of_speakers_as_csv = ""
        for speaker in self.authors.all():
            if is_first_speaker != True:
                # if not the first speaker, add in a comma in CSV string
                list_of_speakers_as_csv += ", "
            list_of_speakers_as_csv += speaker.get_full_name()
            is_first_speaker = False
        return list_of_speakers_as_csv

    get_speakers_as_csv.short_description = 'Speaker List'