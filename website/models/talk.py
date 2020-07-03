from django.db import models
from django.conf import settings
from django.db.models.signals import pre_delete, post_save, m2m_changed, post_delete
from django.dispatch import receiver

from sortedm2m.fields import SortedManyToManyField

import os

from .project_umbrella import Project_umbrella
from .keyword import Keyword
from .person import Person
from .video import Video

class Talk(models.Model):
    title = models.CharField(max_length=255)

    # A talk can be about more than one project
    projects = models.ManyToManyField('Project', blank=True, null=True)
    project_umbrellas = SortedManyToManyField('Project_umbrella', blank=True, null=True)

    # TODO: remove the null = True from all of the following objects
    # including forum_name, forum_url, location, speakers, date, slideshare_url
    keywords = models.ManyToManyField(Keyword, blank=True, null=True)
    forum_name = models.CharField(max_length=255, null=True)
    forum_url = models.URLField(blank=True, null=True)
    location = models.CharField(max_length=255, null=True)

    # Most of the time talks are given by one person, but sometimes they are given by two people
    speakers = models.ManyToManyField(Person, null=True)

    date = models.DateField(null=True)
    slideshare_url = models.URLField(blank=True, null=True)

    # add in video field to address https://github.com/jonfroehlich/makeabilitylabwebsite/issues/539
    video = models.ForeignKey(Video, blank=True, null=True, on_delete=models.DO_NOTHING)

    # The PDF and raw files (e.g., keynote, pptx) are required
    # TODO: remove null=True from these two fields
    pdf_file = models.FileField(upload_to='talks/', null=True, default=None, max_length=255)
    raw_file = models.FileField(upload_to='talks/', blank=True, null=True, default=None, max_length=255)

    INVITED_TALK = "Invited Talk"
    CONFERENCE_TALK = "Conference Talk"
    MS_DEFENSE = "MS Defense"
    PHD_DEFENSE = "PhD Defense"
    GUEST_LECTURE = "Guest Lecture"
    QUALS_TALK = "Quals Talk"

    TALK_TYPE_CHOICES = (
        (INVITED_TALK, INVITED_TALK),
        (CONFERENCE_TALK, CONFERENCE_TALK),
        (MS_DEFENSE, MS_DEFENSE),
        (PHD_DEFENSE, PHD_DEFENSE),
        (GUEST_LECTURE, GUEST_LECTURE),
        (QUALS_TALK, QUALS_TALK),
    )

    talk_type = models.CharField(max_length=50, choices=TALK_TYPE_CHOICES, null=True)

    # The thumbnail should have null=True because it is added automatically later by a post_save signal
    # TODO: decide if we should have this be editable=True and if user doesn't add one him/herself, then
    # auto-generate thumbnail
    thumbnail = models.ImageField(upload_to='talks/images/', editable=False, null=True, max_length=255)

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
        initial_path = instance.pdf_file.path
        person = instance.get_person()
        name = person.last_name
        year = instance.date.year
        title = ''.join(x for x in instance.title.title() if not x.isspace())
        title = ''.join(e for e in title if e.isalnum())

        #change the pdf_file path to point to the renamed file
        instance.pdf_file.name = os.path.join('talks', name + '_' + title + '_' + str(year) + '.pdf')
        new_path = os.path.join(settings.MEDIA_ROOT, instance.pdf_file.name)
        os.rename(initial_path, new_path)
        instance.save()

        # old_pdf_filename_with_path = instance.pdf_file.path
        # new_pdf_filename = get_formatted_filename(instance.get_person(), instance.title, instance.date.year, '.pdf')
        #
        # old_raw_filename_with_path = instance.raw_file.path
        # raw_ext = os.path.splitext(instance.raw_file.path)[1]
        # new_raw_filename = get_formatted_filename(instance.get_person(), instance.title, instance.date.year, raw_ext)

# def get_formatted_filename(person, title_str, year, ext):
#     initial_path = instance.pdf_file.path
#     person = instance.get_person()
#     name = person.last_name
#     year = instance.date.year
#     title = instance.title.title()
#     title = ''.join(x for x in title if not x.isspace())
#     title = ''.join(e for e in title if e.isalnum())
#
#     # change the pdf_file path to point to the renamed file
#     instance.pdf_file.name = os.path.join(dir_name, name + '_' + title + '_' + str(year) + '.pdf')
#     new_path = os.path.join(settings.MEDIA_ROOT, instance.pdf_file.name)
#     os.rename(initial_path, new_path)
#     instance.save()



m2m_changed.connect(update_file_name_talks, sender=Talk.speakers.through)

@receiver(post_delete, sender=Talk)
def talk_delete(sender, instance, **kwargs):
    if instance.pdf_file:
        instance.pdf_file.delete(True)
    if instance.raw_file:
        instance.raw_file.delete(True)
    if instance.thumbnail:
        instance.thumbnail.delete(True)