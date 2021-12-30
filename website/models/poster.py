from django.db import models
from django.dispatch import receiver
from django.conf import settings
from django.db.models.signals import pre_delete, post_save, m2m_changed, post_delete
from django.utils.text import get_valid_filename

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
        initial_path = instance.pdf_file.path
        person = instance.get_person()
        name = person.last_name
        year = instance.date.year
        title = ''.join(x for x in instance.title.title() if not x.isspace())
        title = ''.join(e for e in title if e.isalnum())

        # Convert metadata into a filename
        new_filename = name + '_' + title + '_' + str(year) + '.pdf'

        # Use Django helper function to ensure a clean filename
        new_filename = get_valid_filename(new_filename)

        # Change the pdf_file path to point to the renamed file
        instance.pdf_file.name = os.path.join(Poster.UPLOAD_DIR, new_filename)

        # Add in the media directory
        new_path = os.path.join(settings.MEDIA_ROOT, instance.pdf_file.name)
        
        # Actually rename the existing file (aka initial_path) but only if it exists (it should!)
        if os.path.exists(initial_path):
            os.rename(initial_path, new_path)
            instance.save()
        else:
            _logger.error(f'The file {initial_path} does not exist and cannot be renamed to {new_path}')

        

m2m_changed.connect(update_file_name_poster , sender=Poster.authors.through)

@receiver(pre_delete, sender=Poster)
def poster_delete(sender, instance, **kwargs):
    if instance.pdf_file:
        instance.pdf_file.delete(False)
    if instance.raw_file:
        instance.raw_file.delete(False)
    if instance.thumbnail:
        instance.thumbnail.delete(True)