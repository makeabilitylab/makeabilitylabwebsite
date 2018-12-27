from django.db.models.signals import post_save
from django.dispatch import receiver
from website.models import Talk, Publication, Poster
from wand.image import Image, Color
from django.conf import settings
import os
from django.core.files import File

#
# A note about the @receiver decorator used in signals.py.
# There are two ways to hook up receiver functions
# 1. You can hook them up manually:
#     from django.core.signals import request_finished
#     request_finished.connect(my_callback)
#
# 2. You can use a receiver() decorator (the @receiver thing). This is the approach we are using.
#    In order for this to work, we must add in an import website.signals to the ready() function
#    in apps.py, which we've done.
# See : https://docs.djangoproject.com/en/1.9/topics/signals/#receiver-functions
#

# Called automatically by Django after Publication is saved using Django's
# built-in signal dispatch functionality. We use this function to do some
# post-processong on the uploaded Publication data like auto-generating a thumbnail
# For more info on Django signal dispatch, see: https://docs.djangoproject.com/en/1.9/topics/signals/
@receiver(post_save, sender=Publication)
def publication_post_save(sender, **kwargs):
    # See: http://www.yaconiello.com/blog/auto-generating-pdf-covers/
    # http://stackoverflow.com/questions/1308386/programmatically-saving-image-to-django-imagefield

    # get the publication that was just saved and auto-generate a thumbnail

    pub = kwargs['instance']
    if pub.pdf_file:
        print("Publication '{}' has just been saved with PDF={}, checking to see if we should auto-generate a thumbnail".format(pub.title, pub.pdf_file.path))
        thumbnail_res = 300
        generate_and_save_thumbnail_from_pdf(pub, thumbnail_res)

# Called automatically by Django after Talk is saved using Django's
# built-in signal dispatch functionality. We use this function to do some
# post-processong on the uploaded Talk data like auto-generating a thumbnail
# For more info on Django signal dispatch, see: https://docs.djangoproject.com/en/1.9/topics/signals/
@receiver(post_save, sender=Talk)
def talk_post_save(sender, **kwargs):
    # See: http://www.yaconiello.com/blog/auto-generating-pdf-covers/
    # http://stackoverflow.com/questions/1308386/programmatically-saving-image-to-django-imagefield

    # get the talk that was just saved and auto-generate a thumbnail
    talk = kwargs['instance']
    if talk.pdf_file:
        print("Talk '{}' has just been saved with PDF={}, checking to see if we should auto-generate a thumbnail".format(talk.title, talk.pdf_file.path))
        thumbnail_res = 300
        generate_and_save_thumbnail_from_pdf(talk, thumbnail_res)

# Assumes that artifact is a models.Model type and has the following fields:
#  an ImageField called thumbnail
#  a FileField called pdf_file
def generate_and_save_thumbnail_from_pdf(artifact, thumbnail_resolution):
    thumbnail_dir = os.path.normpath(
        os.path.normcase(os.path.join(settings.MEDIA_ROOT, artifact.thumbnail.field.upload_to)))

    # make sure this dir exists
    if not os.path.exists(thumbnail_dir):
        os.makedirs(thumbnail_dir)

    pdf_filename = os.path.basename(artifact.pdf_file.path)
    pdf_filename_no_extension = os.path.splitext(pdf_filename)[0]
    thumbnail_filename = "{}.{}".format(pdf_filename_no_extension, 'jpeg');
    thumbnail_path = os.path.join(thumbnail_dir, thumbnail_filename)

    # check to see if this is a new (or changed) file. This 'if condition' is super necessary
    # because otherwise we would enter an infinite loop given that we save the model again below
    if not artifact.thumbnail or artifact.thumbnail.name is None or \
            os.path.normpath(os.path.normcase(artifact.thumbnail.path)) != os.path.normpath(
        os.path.normcase(thumbnail_path)):
        with Image(filename="{}[0]".format(artifact.pdf_file.path), resolution=300) as img:
            img.format = 'jpeg'
            img.background_color = Color('white')
            img.alpha_channel = 'remove'
            img.save(filename=thumbnail_path)

        # talk.thumbnail = thumbnail_path
        relative_thumbnail_path = os.path.join(artifact.thumbnail.field.upload_to, thumbnail_filename)
        artifact.thumbnail = relative_thumbnail_path

        artifact.save()
    else:
        print("No need to save, the thumbnail '{}' already exists!".format(thumbnail_path))