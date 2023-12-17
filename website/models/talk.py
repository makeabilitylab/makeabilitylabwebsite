import os
from website.models import Artifact
from django.db import models

class Talk(Artifact):
    UPLOAD_DIR = 'talks/'
    THUMBNAIL_DIR = os.path.join(UPLOAD_DIR, 'images/')

    slideshare_url = models.URLField(blank=True, null=True)
    slideshare_url.help_text = "Slideshare is no longer a popular way of sharing talks"

    # add in video field to address https://github.com/jonfroehlich/makeabilitylabwebsite/issues/539
    video = models.ForeignKey('Video', blank=True, null=True, on_delete=models.DO_NOTHING)
    video.help_text = "If there is a video recording of the talk, add it here."

    INVITED_TALK = "Invited Talk"
    CONFERENCE_TALK = "Conference Talk"
    MS_DEFENSE = "MS Defense"
    PHD_DEFENSE = "PhD Defense"
    GUEST_LECTURE = "Guest Lecture"
    QUALS_TALK = "Quals Talk"
    KEYNOTE_TALK = "Keynote Talk"

    TALK_TYPE_CHOICES = (
        (INVITED_TALK, INVITED_TALK),
        (CONFERENCE_TALK, CONFERENCE_TALK),
        (MS_DEFENSE, MS_DEFENSE),
        (PHD_DEFENSE, PHD_DEFENSE),
        (GUEST_LECTURE, GUEST_LECTURE),
        (QUALS_TALK, QUALS_TALK),
        (KEYNOTE_TALK, KEYNOTE_TALK),
    )

    talk_type = models.CharField(max_length=50, choices=TALK_TYPE_CHOICES, null=True)
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