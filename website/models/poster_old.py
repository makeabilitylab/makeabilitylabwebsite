from django.db import models
from django.dispatch import receiver
from django.conf import settings
from django.db.models.signals import pre_delete, post_save, m2m_changed, post_delete
import website.utils.fileutils as ml_fileutils

import datetime
import os

import os
import os.path
import logging

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

class Poster(models.Model):

    @staticmethod
    def get_upload_to(poster, original_filename):
        """Sets up the filename for this poster"""
        old_filename_ext = os.path.splitext(original_filename)[1]
        new_filename_with_ext = Poster.generate_filename(poster, old_filename_ext)
        new_filename_with_path = os.path.join(Poster.UPLOAD_DIR, new_filename_with_ext)
        _logger.debug(f"For poster {poster}, we renamed the file from {original_filename} to {new_filename_with_path}")
        return new_filename_with_path

    UPLOAD_DIR = 'posters/' # relative path
    THUMBNAIL_DIR = os.path.join(UPLOAD_DIR, 'images/') # relative path

    title = models.CharField(max_length=255, blank=True, null=True)
    authors = models.ManyToManyField('Person', blank=True) # a poster can have multiple authors
    projects = models.ManyToManyField('Project', blank=True) # a poster can be about multiple projects
    date = models.DateField(null=True)

    # The PDF and raw files (e.g., illustrator, powerpoint)
    pdf_file = models.FileField(upload_to=get_upload_to, null=True, default=None, max_length=255)
    raw_file = models.FileField(upload_to=get_upload_to, blank=True, null=True, default=None, max_length=255)

    forum_name = models.CharField(max_length=255, null=True)
    forum_name.help_text = "What is the name of the poster venue?"

    # The thumbnail should have null=True because it is added automatically later by a post_save signal
    # TODO: decide if we should have this be editable=True and if user doesn't add one him/herself, then
    # auto-generate thumbnail
    thumbnail = models.ImageField(upload_to=THUMBNAIL_DIR, editable=False, null=True, max_length=255)

    def get_person(self):
        """Returns the first author of the poster"""
        return self.authors.all()[0]

    def __str__(self):
        first_author = self.authors.all()[0]
        return f"{first_author.last_name} {self.title} {self.forum_name} {self.date}"
    
    def save(self, *args, **kwargs):
        """Override save to make sure the filename stays up-to-date with metadata"""
        if self.pk is not None: # if this is not our first time saving the object
            
            # Get the original poster
            orig_poster = Poster.objects.get(pk=self.pk)

            # Check if fields we use in the filename have changed
            if (orig_poster.title != self.title or
                orig_poster.get_person() != self.get_person() or
                orig_poster.date != self.date or
                orig_poster.forum_name != self.forum_name):

                _logger.debug(f"The original poster {orig_poster} and modified poster {self} have different metadata that affects the filename, renaming...")
                new_filename_no_ext = Poster.generate_filename(self)
                ml_fileutils.rename_artifact_in_db_and_filesystem(self, self.pdf_file, new_filename_no_ext)

            # Check if the pdf_file has changed. If it has, delete the thumbnail so a new one will be generated
            # in the post_save signal
            if (orig_poster.pdf_file != self.pdf_file):
                _logger.debug(f"In poster {self}, it appears the pdf file has changed from {orig_poster.pdf_file} to {self.pdf_file}")

                # If self.thumbnail exists, delete it so it will be auto-generated with a new file
                if self.thumbnail:
                    self.thumbnail.delete(True)

        super().save(*args, **kwargs)

    @staticmethod
    def generate_filename(poster, file_extension=None):
        """Generates a filename for this talk instance"""
        if file_extension is None:
            return ml_fileutils.get_filename_without_ext_for_artifact(
                    poster.get_person().last_name, poster.title, 
                    poster.forum_name, poster.date)
        else:
            return ml_fileutils.get_filename_for_artifact(
                    poster.get_person().last_name, poster.title, 
                    poster.forum_name, poster.date, file_extension)

def update_filename_poster(sender, instance, action, reverse, **kwargs):
    # Reverse: Indicates which side of the relation is updated (i.e., if it is the forward or reverse relation that is being modified)
    # Action: A string indicating the type of update that is done on the relation.
    # post_add: Sent after one or more objects are added to the relation

    # TODO: I think we may want to change this to an upload_to functionality like we do in person.py
    # because of the thumbnail generation. We could also take care of the thumbnail generation there imo
    # rather than in website/signals.py
    #
    # 0. What's advantage of changing upload_to to a function vs. action post_add? I suppose upload_to 
    #    doesn't work if we change some attribute that affects the filename like venue or date?
    # 1. What's the advantage of post_save vs. just actually overwriting save? Maybe post_save is async?
    #    Also, how can we control order. Does the signals.py happen before this post_add?
    # 2. How can I check if a new pdf_file has been changed on an admin change? If new one added, have to generate new thumbnail
    # 3. Check if we add a new pdf to an existing pub or talk that it triggers a new thumbnail creation
    # 4. Add in Poster as a suffix and Talk as a suffix
    # 5. How would I check if a new pdf_file has been uploaded and then generate a new thumb nail

    print("I COMMENTED OUT THIS CODE FOR NOW IN update_filename_poster")
    # if action == 'post_add' and not reverse:

    #      # Convert metadata into a filename
    #     new_filename_no_ext = Poster.generate_filename(instance)
        
    #     # Rename the database entry and file on filesystem
    #     if instance.pdf_file:
    #         new_pdf_filename_with_path = ml_fileutils.rename_artifact_in_db_and_filesystem(instance.pdf_file, new_filename_no_ext)
    #         if new_pdf_filename_with_path is not None:
    #             instance.save()
        
    #     # Rename the database entry and file on filesystem
    #     if instance.raw_file:
    #         new_raw_filename_with_path = ml_fileutils.rename_artifact_in_db_and_filesystem(instance.raw_file, new_filename_no_ext)
    #         if new_raw_filename_with_path is not None:
    #             instance.save()

m2m_changed.connect(update_filename_poster, sender=Poster.authors.through)

@receiver(pre_delete, sender=Poster)
def poster_delete(sender, instance, **kwargs):
    if instance.pdf_file:
        instance.pdf_file.delete(False)
    if instance.raw_file:
        instance.raw_file.delete(False)
    if instance.thumbnail:
        instance.thumbnail.delete(True)