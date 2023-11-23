from django.db import models
from django.conf import settings
from django.db.models.signals import pre_delete, post_save, m2m_changed, post_delete
from django.dispatch import receiver

from sortedm2m.fields import SortedManyToManyField

import website.utils.fileutils as ml_fileutils

import os
import os.path
import logging

from .project_umbrella import ProjectUmbrella
from .keyword import Keyword
from .person import Person
from .video import Video

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

class Talk(models.Model):
    UPLOAD_DIR = 'talks/' # relative path
    THUMBNAIL_DIR = os.path.join(UPLOAD_DIR, 'images/') # relative path

    title = models.CharField(max_length=255)

    # A talk can be about more than one project
    projects = models.ManyToManyField('Project', blank=True)
    projects.help_text = "Most conference talks are associated with only one project but "\
                         "keynotes, guest lectures, etc. might be associated with multiple projectss"
    project_umbrellas = SortedManyToManyField('ProjectUmbrella', blank=True)

    # TODO: remove the null = True from all of the following objects
    # including forum_name, forum_url, location, speakers, date, slideshare_url
    keywords = models.ManyToManyField(Keyword, blank=True)
    keywords.help_text = "The keywords associated with this talk"

    forum_name = models.CharField(max_length=255, null=True)
    forum_name.help_text = "What is the name of the speaking venue?"

    forum_url = models.URLField(blank=True, null=True)
    forum_url.help_text = "A hyperlink to the speaking forum (<i>e.g.,</i> if CHI, put https://chi2024.acm.org/)"

    location = models.CharField(max_length=255, null=True)
    location.help_text = "The geographic location of the talk"

    # Most of the time talks are given by one person, but sometimes they are given by two people
    speakers = models.ManyToManyField(Person)
    speakers.help_text = "Most of the time, talks are given by one person but there are exceptions"

    date = models.DateField(null=True)
    date.help_text = "The date of the talk"

    slideshare_url = models.URLField(blank=True, null=True)
    slideshare_url.help_text = "Slideshare is no longer a popular way of sharing talks"

    # add in video field to address https://github.com/jonfroehlich/makeabilitylabwebsite/issues/539
    video = models.ForeignKey(Video, blank=True, null=True, on_delete=models.DO_NOTHING)
    video.help_text = "If there is a video recording of the talk, add it here."

    # The PDF and raw files (e.g., keynote, pptx) are required
    # TODO: remove null=True from these two fields
    pdf_file = models.FileField(upload_to=UPLOAD_DIR, null=True, default=None, max_length=255)
    pdf_file.help_text = "The PDF of the talk"
    
    raw_file = models.FileField(upload_to=UPLOAD_DIR, blank=True, null=True, default=None, max_length=255)
    raw_file.help_text = "The raw file (e.g., pptx, keynote) for the talk. While not required, this is "\
        "<b>highly</b> recommended as it creates a better archive of the work"

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

    # The thumbnail should have null=True because it is added automatically later by a post_save signal
    # TODO: decide if we should have this be editable=True and if user doesn't add one him/herself, then
    # auto-generate thumbnail
    thumbnail = models.ImageField(upload_to=THUMBNAIL_DIR, editable=False, null=True, max_length=255)

    # raw_file = models.FileField(upload_to='talks/')
    # print("In talk model!")
    def get_person(self):
        """Gets the "first author" (or speaker in this case) for the talk"""
        return self.speakers.all()[0]

    def get_speakers_as_csv(self):
        """Gets the list of speakers as a csv string"""
        # iterate through all of the speakers and return the csv
        is_first_speaker = True
        list_of_speakers_as_csv = ""
        for speaker in self.speakers.all():
            if is_first_speaker != True:
                # if not the first speaker, add in a comma in CSV string
                list_of_speakers_as_csv += ", "
            list_of_speakers_as_csv += speaker.get_full_name()
            is_first_speaker = False
        return list_of_speakers_as_csv

    get_speakers_as_csv.short_description = 'Speaker List'

    def __str__(self):
        return "{}, {}, {} {}".format(self.get_person().get_full_name(), self.title, self.forum_name, self.date)

#@receiver(post_save, sender=Talk)
def update_file_name_talks(sender, instance, action, reverse, **kwargs):
    #Reverse: Indicates which side of the relation is updated (i.e., if it is the forward or reverse relation that is being modified)
    #Action: A string indicating the type of update that is done on the relation.
    #post_add: Sent after one or more objects are added to the relation

    # from: https://docs.djangoproject.com/en/2.1/ref/signals/
    if action == 'post_add' and not reverse:

        # Convert metadata into a filename
        new_filename_no_ext = ml_fileutils.get_filename_without_ext_for_artifact(
            instance.get_person().last_name, instance.title, instance.forum_name,
            instance.date)
        
        # Rename the database entry and file on filesystem
        if instance.pdf_file:
            new_pdf_filename_with_path = ml_fileutils.rename(instance.pdf_file, new_filename_no_ext)
            if new_pdf_filename_with_path is not None:
                instance.save()
        
        # Rename the database entry and file on filesystem
        if instance.raw_file:
            new_raw_filename_with_path = ml_fileutils.rename(instance.raw_file, new_filename_no_ext)
            if new_raw_filename_with_path is not None:
                instance.save()
        
m2m_changed.connect(update_file_name_talks, sender=Talk.speakers.through)

@receiver(post_delete, sender=Talk)
def talk_delete(sender, instance, **kwargs):
    if instance.pdf_file:
        instance.pdf_file.delete(True)
    if instance.raw_file:
        instance.raw_file.delete(True)
    if instance.thumbnail:
        instance.thumbnail.delete(True)