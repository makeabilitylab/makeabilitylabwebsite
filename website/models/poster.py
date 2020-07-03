from django.db import models
from django.dispatch import receiver
from django.conf import settings
from django.db.models.signals import pre_delete, post_save, m2m_changed, post_delete

import datetime
import os

class Poster(models.Model):

    title = models.CharField(max_length=255, blank=True, null=True)
    authors = models.ManyToManyField('Person', blank=True, null=True) # a poster can have multiple authors
    projects = models.ManyToManyField('Project', blank=True, null=True) # a poster can be about multiple projects
    date = models.DateField(null=True)

    # The PDF and raw files (e.g., illustrator, powerpoint)
    pdf_file = models.FileField(upload_to='posters/', null=True, default=None, max_length=255)
    raw_file = models.FileField(upload_to='posters/', blank=True, null=True, default=None, max_length=255)

    # The thumbnail should have null=True because it is added automatically later by a post_save signal
    # TODO: decide if we should have this be editable=True and if user doesn't add one him/herself, then
    # auto-generate thumbnail
    thumbnail = models.ImageField(upload_to='posters/images/', editable=False, null=True, max_length=255)

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


        #change the path of the pdf file to point to the new file name
        instance.pdf_file.name = os.path.join('posters', name + '_' + title + '_' + str(year) + '.pdf')
        new_path = os.path.join(settings.MEDIA_ROOT, instance.pdf_file.name)
        os.rename(initial_path, new_path)
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