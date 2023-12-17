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
    forum_name.help_text = "What is the name of the speaking venue? Please use a short name like UIST, ASSETS, CHI, etc."

    forum_url = models.URLField(blank=True, null=True)
    forum_url.help_text = "A hyperlink to the speaking forum (<i>e.g.,</i> if CHI, put https://chi2024.acm.org/)"

    location = models.CharField(max_length=255, null=True)
    location.help_text = "The geographic location of the talk"

    # Most of the time talks are given by one person, but sometimes they are given by two people
    authors = models.ManyToManyField(Person)
    authors.help_text = "Most of the time, talks are given by one person but there are exceptions"

    date = models.DateField(null=True)
    date.help_text = "The date of the talk"

    slideshare_url = models.URLField(blank=True, null=True)
    slideshare_url.help_text = "Slideshare is no longer a popular way of sharing talks"

    # add in video field to address https://github.com/jonfroehlich/makeabilitylabwebsite/issues/539
    video = models.ForeignKey(Video, blank=True, null=True, on_delete=models.DO_NOTHING)
    video.help_text = "If there is a video recording of the talk, add it here."

    # The PDF and raw files (e.g., keynote, pptx) are required
    # TODO: remove null=True from these two fields
    # Note: we cannot setup the filename here with a custom upload_to function like we do in Person
    # because the filename depends on the first speaker, which is a many-to-many relation
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

    def __str__(self):
        if self.id and self.authors.exists():
            return "{}, '{}', {} {}".format(self.get_person().get_full_name(), self.title, self.forum_name, self.date)
        else:
            return f"Unknown, '{self.title}', {self.forum_name}, {self.date}"

    def save(self, *args, **kwargs):
        
        _logger.debug(f"Started save for self={self} with talk id={self.pk} and args={args} and kwargs={kwargs}")
        _logger.debug(f"The pdf_file is currently {self.pdf_file}")
        if self.pdf_file:
            # In Django, when you call save() on a model instance, the FileField doesn’t immediately have its full path set. 
            # This is because the file hasn’t been saved to the storage system yet.
            _logger.debug(f"The local pdf_file path is: {self.pdf_file.name}")

            # This won't be correct until super.save() is called (the first time this Talk instance is created)
            _logger.debug(f"The full pdf_file path is: {self.pdf_file.path}") 

        _logger.debug(f"The raw_file is currently {self.raw_file}")

        first_time_saved = self.id is None
        _logger.debug(f"For talk.id={self.id}, first_time_saved={first_time_saved}")
        
        if not first_time_saved and kwargs.get('update_fields') is not None:
            update_fields = kwargs['update_fields']
            _logger.debug(f"update_fields={update_fields}, checking to see if we have to do some cleanup on files")
            orig_talk = Talk.objects.get(pk=self.pk)

            # Check if pdf_file is one of the updated fields and, if so, delete the old file
            if 'pdf_file' in update_fields:
                _logger.debug(f"pdf_file is in update_fields, attempting to delete old pdf_file and corresponding thumbnail")
                if orig_talk.pdf_file:
                    _logger.debug(f"orig_talk.pdf_file={orig_talk.pdf_file} exists, attempting to delete")
                    if orig_talk.pdf_file.storage.exists(orig_talk.pdf_file.name):
                        # The True argument in pdf_file.delete(True) is for the save parameter. This parameter determines 
                        # whether to save the model after the file has been deleted. If save is True, the model will be 
                        # saved after the file deletion. Since we're already in a save(), we don't want to call save
                        deleted_path = orig_talk.pdf_file.path
                        orig_talk.pdf_file.delete(False)
                        _logger.debug(f"Deleted pdf_file={deleted_path} off filesystem")
                    else:
                        _logger.debug(f"Could not delete pdf_file={orig_talk.pdf_file} as it does not exist on filesystem")

                if orig_talk.thumbnail:
                    _logger.debug(f"orig_talk.thumbnail={orig_talk.thumbnail} exists, attempting to delete")
                    if orig_talk.thumbnail.storage.exists(orig_talk.thumbnail.name):
                        deleted_path = orig_talk.thumbnail.path
                        orig_talk.thumbnail.delete(False)
                        _logger.debug(f"Deleted thumbnail={deleted_path} off filesystem")
                    else:
                        _logger.debug(f"Could not delete thumbnail={orig_talk.thumbnail} as it does not exist on filesystem")
            
            if 'raw_file' in update_fields:
                _logger.debug(f"raw_file is in update_fields, attempting to delete old raw_file")
                if orig_talk.raw_file:
                    _logger.debug(f"Attempting to delete raw_file={orig_talk.raw_file} off filesystem")
                    if orig_talk.raw_file:
                        if orig_talk.raw_file.storage.exists(orig_talk.raw_file.name):
                            deleted_path = orig_talk.raw_file.path
                            orig_talk.raw_file.delete(False)
                            _logger.debug(f"Deleted raw_file={deleted_path} off filesystem")
                        else:
                            _logger.debug(f"Could not delete raw_file={orig_talk.raw_file} as it does not exist on filesystem")

        if not first_time_saved:
            # self.speakers is a many-to-many field in Django. This field is not set
            # until after this model is first saved to the database (which is a bit funky)
            # This means that self.speakers can't get set until after this save method completes the 
            # first time (that is, after super().save is called)
            # Hence, we have a flag "first_time_saved" that checks for this condition and
            # then attempts to continue only when speaker values have been set
            _logger.debug(f"The speakers for the talk are: {self.authors.all()}")
            if self.authors.exists():
                _logger.debug(f"A speaker exists, checking to see if filenames need to be renamed")
                if Talk.do_filenames_need_updating(self):
                    new_filename_no_ext = Talk.generate_filename(self)

                    if self.pdf_file:
                        old_pdf_filename = os.path.basename(self.pdf_file.name)
                        old_pdf_filename_no_ext, ext = os.path.splitext(old_pdf_filename)
                        if new_filename_no_ext != old_pdf_filename_no_ext:
                            _logger.debug(f"The new_filename_no_ext={new_filename_no_ext} and old_pdf_filename_no_ext={old_pdf_filename_no_ext} don't match. Renaming...")
                            ml_fileutils.rename_artifact_on_filesystem(self.pdf_file, new_filename_no_ext)
                    
                    if self.raw_file:
                        old_raw_filename = os.path.basename(self.pdf_file.name)
                        old_raw_filename_no_ext, ext = os.path.splitext(old_raw_filename)
                        if new_filename_no_ext != old_raw_filename_no_ext:
                            _logger.debug(f"The new_filename_no_ext={new_filename_no_ext} and old_raw_filename_no_ext={old_raw_filename_no_ext} don't match. Renaming...")
                            ml_fileutils.rename_artifact_on_filesystem(self.raw_file, new_filename_no_ext)

                    if self.thumbnail:
                        old_thumbnail_filename = os.path.basename(self.pdf_file.name)
                        old_thumbnail_filename_no_ext, ext = os.path.splitext(old_thumbnail_filename)
                        if new_filename_no_ext != old_thumbnail_filename_no_ext:
                            _logger.debug(f"The new_filename_no_ext={new_filename_no_ext} and old_thumbnail_filename_no_ext={old_thumbnail_filename_no_ext} don't match. Renaming...")
                            ml_fileutils.rename_artifact_on_filesystem(self.thumbnail, new_filename_no_ext)
            else:
                _logger.debug("No speakers exist yet, so will wait for m2m speakers_changed to rename files")

            # Generate a thumbnail if one does not already exist
            pdf_filename = os.path.basename(self.pdf_file.name)
            pdf_filename_no_ext, ext = os.path.splitext(pdf_filename)
            thumbnail_filename = os.path.basename(pdf_filename_no_ext) + ".jpg" 
            thumbnail_filename_with_local_path = os.path.join(self.thumbnail.field.upload_to, thumbnail_filename)
            thumbnail_exists_in_storage = self.thumbnail.storage.exists(thumbnail_filename_with_local_path)
            if not self.thumbnail or not thumbnail_exists_in_storage:
                _logger.debug(f"The thumbnail for talk.id={self.id} does not exist at {thumbnail_filename_with_local_path}, generating...")
                
                # generate a thumbnail
                if self.pdf_file.storage.exists(self.pdf_file.name):
                    ml_fileutils.generate_thumbnail_for_pdf(self.pdf_file, self.thumbnail)
                else:
                    _logger.debug(f"Could not generate a thumbnail because the pdf {self.pdf_file.path} was not found in storage")
            elif thumbnail_exists_in_storage:
                _logger.debug(f"The thumbnail for talk.id={self.id} already exists at {thumbnail_filename_with_local_path}, so not generating")

        _logger.debug(f"Calling super().save(*args, **kwargs)")

        super().save(*args, **kwargs)

        _logger.debug(f"Completed save for self={self} with talk id={self.pk} and args={args} and kwargs={kwargs}")

    @staticmethod
    def do_filenames_need_updating(talk):
        new_filename_no_ext = Talk.generate_filename(talk)

        if talk.pdf_file:
            # We get the old filename (without the local path)
            old_pdf_filename = os.path.basename(talk.pdf_file.name)
            old_pdf_filename_no_ext, ext = os.path.splitext(old_pdf_filename)
            if new_filename_no_ext != old_pdf_filename_no_ext:
                _logger.debug(f"The new_filename_no_ext={new_filename_no_ext} and old_pdf_filename_no_ext={old_pdf_filename_no_ext} don't match")
                return True
        
        if talk.raw_file:
            old_raw_filename = os.path.basename(talk.pdf_file.name)
            old_raw_filename_no_ext, ext = os.path.splitext(old_raw_filename)
            if new_filename_no_ext != old_raw_filename_no_ext:
                _logger.debug(f"The new_filename_no_ext={new_filename_no_ext} and old_raw_filename_no_ext={old_raw_filename_no_ext} don't match")
                return True
        
        if talk.thumbnail:
            old_thumbnail_filename = os.path.basename(talk.pdf_file.name)
            old_thumbnail_filename_no_ext, ext = os.path.splitext(old_thumbnail_filename)
            if new_filename_no_ext != old_thumbnail_filename_no_ext:
                _logger.debug(f"The new_filename_no_ext={new_filename_no_ext} and old_thumbnail_filename_no_ext={old_thumbnail_filename_no_ext} don't match")
                return True

        return False

    @staticmethod
    def generate_filename(talk, file_extension=None):
        """Generates a filename for this talk instance"""
        if file_extension is None:
            return ml_fileutils.get_filename_without_ext_for_artifact(
                    talk.get_first_speaker_last_name(), talk.title, 
                    talk.forum_name, talk.date)
        else:
            return ml_fileutils.get_filename_for_artifact(
                    talk.get_first_speaker_last_name(), talk.title, 
                    talk.forum_name, talk.date, file_extension)

def speakers_changed(sender, instance, action, reverse, **kwargs):
    #Reverse: Indicates which side of the relation is updated (i.e., if it is the forward or reverse relation that is being modified)
    #Action: A string indicating the type of update that is done on the relation.
    #post_add: Sent after one or more objects are added to the relation

    _logger.debug(f"Started speakers_changed with sender={sender}, instance={instance}, action={action}, reverse={reverse}, and kwargs={kwargs}")
    
    if action == 'post_add' and not reverse:
        # The speakers field is a many-to-many field, which is handled differently than other fields in Django
        # When a talk object is first created and save called (to save the object back to the database),
        # the speakers field is not yet set. It is not set until after super.save() is completed
        # So, we use this speakers_changed signal to both listen for when the assigned speaker is
        # initially setup and for when it is changed
        if Talk.do_filenames_need_updating(instance):
            _logger.debug("Filenames need to be updated, calling talk.save()")
            instance.save()

    _logger.debug(f"Completed speakers_changed")
        
m2m_changed.connect(speakers_changed, sender=Talk.authors.through)

@receiver(post_delete, sender=Talk)
def talk_post_delete(sender, instance, **kwargs):
    _logger.debug(f"Started talk_post_delete with sender={sender}, instance={instance}, kwargs={kwargs}")
   
    _logger.debug(f"Attempting to delete pdf_file={instance.pdf_file} off filesystem")
    if instance.pdf_file:
        if instance.pdf_file.storage.exists(instance.pdf_file.name):
            instance.pdf_file.delete(True)
            _logger.debug(f"Deleted pdf_file={instance.pdf_file} off filesystem")
        else:
            _logger.debug(f"Could not delete pdf_file={instance.pdf_file} as it does not exist on filesystem")
    
    _logger.debug(f"Attempting to delete raw_file={instance.raw_file} off filesystem")
    if instance.raw_file:
        if instance.raw_file.storage.exists(instance.raw_file.name):
            instance.raw_file.delete(True)
            _logger.debug(f"Deleted raw_file={instance.raw_file} off filesystem")
        else:
            _logger.debug(f"Could not delete raw_file={instance.raw_file} as it does not exist on filesystem")

    _logger.debug(f"Attempting to delete thumbnail={instance.thumbnail} off filesystem")
    if instance.thumbnail:
        if instance.thumbnail.storage.exists(instance.thumbnail.name):
            instance.thumbnail.delete(True)
            _logger.debug(f"Deleted thumbnail={instance.thumbnail} off filesystem")
        else:
            _logger.debug(f"Could not delete thumbnail={instance.thumbnail} as it does not exist on filesystem")