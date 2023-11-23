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
    UPLOAD_DIR = 'posters/' # relative path
    THUMBNAIL_DIR = os.path.join(UPLOAD_DIR, 'images/') # relative path

    title = models.CharField(max_length=255, blank=True, null=True)
    authors = models.ManyToManyField('Person', blank=True) # a poster can have multiple authors
    projects = models.ManyToManyField('Project', blank=True) # a poster can be about multiple projects
    date = models.DateField(null=True)

    # The PDF and raw files (e.g., illustrator, powerpoint)
    pdf_file = models.FileField(upload_to=UPLOAD_DIR, null=True, default=None, max_length=255)
    raw_file = models.FileField(upload_to=UPLOAD_DIR, blank=True, null=True, default=None, max_length=255)

    forum_name = models.CharField(max_length=255, null=True)
    forum_name.help_text = "What is the name of the speaking venue?"
    
    # The thumbnail should have null=True because it is added automatically later by a post_save signal
    # TODO: decide if we should have this be editable=True and if user doesn't add one him/herself, then
    # auto-generate thumbnail
    thumbnail = models.ImageField(upload_to=THUMBNAIL_DIR, editable=False, null=True, max_length=255)

    def get_person(self):
        """Returns the first speaker"""
        return self.authors.all()[0]

    def __str__(self):
        return "{}, {}, {}".format(self.get_person().get_full_name(), self.title, self.date)

def update_file_name_poster(sender, instance, action, reverse, **kwargs):
    # Reverse: Indicates which side of the relation is updated (i.e., if it is the forward or reverse relation that is being modified)
    # Action: A string indicating the type of update that is done on the relation.
    # post_add: Sent after one or more objects are added to the relation
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

m2m_changed.connect(update_file_name_poster , sender=Poster.authors.through)

@receiver(pre_delete, sender=Poster)
def poster_delete(sender, instance, **kwargs):
    if instance.pdf_file:
        instance.pdf_file.delete(False)
    if instance.raw_file:
        instance.raw_file.delete(False)
    if instance.thumbnail:
        instance.thumbnail.delete(True)