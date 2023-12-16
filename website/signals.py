from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from website.models import Talk, Publication, Poster, Artifact
from wand.image import Image, Color
from django.conf import settings
import os
from django.core.files import File
import website.utils.fileutils as ml_fileutils

import logging

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

#
# A note about the @receiver decorator used in signals.py.
# There are two ways to hook up receiver functions
# 1. You can hook them up manually:
#     from django.core.signals import request_finished
#     request_finished.connect(my_callback)
#
# 2. You can use a receiver() decorator (the @receiver construct). This is the approach we are using.
#    In order for this to work, we must add in an import website.signals to the ready() function
#    in apps.py, which we've done.
# See : https://docs.djangoproject.com/en/1.9/topics/signals/#receiver-functions
#

@receiver(m2m_changed, sender=Poster.authors.through)
@receiver(m2m_changed, sender=Talk.authors.through)
@receiver(m2m_changed, sender=Publication.authors.through)
def authors_changed(sender, instance, action, reverse, **kwargs):
    """
    Signal receiver for changes in the 'authors' field of Poster, Talk, and Publication models.

    This function is triggered when the 'authors' field of an instance of any of the above models is modified.
    It checks if the filenames of the instance need to be updated whenever authors are added and the change is not a reverse relation.

    Parameters:
    sender (Model): The model class that the authors field belongs to. It could be Poster, Talk, or Publication.
    instance (Model instance): The actual instance of the sender model class that is being modified.
    action (str): The type of operation performed on the many-to-many field. It can be one of the following:
                  - "pre_add": Sent before one or more objects are added to the relation.
                  - "post_add": Sent after one or more objects have been added to the relation.
                  - "pre_remove": Sent before one or more objects are removed from the relation.
                  - "post_remove": Sent after one or more objects have been removed from the relation.
                  - "pre_clear": Sent before the relation is cleared.
                  - "post_clear": Sent after the relation has been cleared.
    reverse (bool): A flag indicating the direction of the relation:
                    - If `False`, the modification was made from the instance side.
                    - If `True`, the modification was made from the related object side.
    **kwargs: Additional keyword arguments.

    Returns:
    None
    """
    _logger.debug(
        f"Started authors_changed with sender={sender}, instance={instance}, "
        f"action={action}, reverse={reverse}, and kwargs={kwargs}"
    )
    
    if action == 'post_add' and not reverse:
        # The authors field is a many-to-many field, which is handled differently than other fields in Django
        # When an artifact object is first created and save called (to save the object back to the database),
        # the authors field is not yet set. It won't be set until after super.save() is completed the first time
        # So, we use this authors_changed signal to both listen for when the assigned author is
        # initially setup and for when it is changed (e.g., if the first author changes)
        if Artifact.do_filenames_need_updating(instance):
            _logger.debug("Filenames need to be updated, calling instance.save()")
            instance.save()

    _logger.debug(f"Completed authors_changed")

    

# Called automatically by Django after Publication is saved using Django's
# built-in signal dispatch functionality. We use this function to do some
# post-processing on the uploaded Publication data like auto-generating a thumbnail
# For more info on Django signal dispatch, see: https://docs.djangoproject.com/en/1.9/topics/signals/
@receiver(post_save, sender=Publication)
def publication_post_save(sender, **kwargs):
    # See: http://www.yaconiello.com/blog/auto-generating-pdf-covers/
    # http://stackoverflow.com/questions/1308386/programmatically-saving-image-to-django-imagefield

    # get the publication that was just saved and auto-generate a thumbnail
    pub = kwargs['instance']
    if pub.pdf_file:
        _logger.debug("Publication '{}' has just been saved with PDF={}, checking to see if we should auto-generate a thumbnail".format(pub.title, pub.pdf_file.path))
        thumbnail_res = 300
        generate_and_save_thumbnail_from_pdf(pub, thumbnail_res)

# Called automatically by Django after Talk is saved using Django's
# built-in signal dispatch functionality. We use this function to do some
# post-processing on the uploaded Talk data like auto-generating a thumbnail
# For more info on Django signal dispatch, see: https://docs.djangoproject.com/en/1.9/topics/signals/
@receiver(post_save, sender=Talk)
def talk_post_save(sender, **kwargs):
    _logger.debug(f"Started talk_post_save with sender={sender} and kwargs={kwargs}")

    # Note to the reader:
    # I considered putting the talk file renaming code (currently in Talk.save()) here; however,
    # this proved impossible because talk_post_save is called before Talk.speakers_changed and so
    # we can't get access to the speaker (as a many-to-many foreign field) until after speakers_changed
    # I just wanted to add this note for rationale for *why* it's not here in case a future brain 
    # thinks it would be a better fit here.
    #
    # Note also that we used to do our PDF thumbnail generation here but I consolidated it
    # in talk.save() to keep all of this code in one place
  
    talk = kwargs['instance']
    _logger.debug(f"Speakers: {talk.speakers.all()}")

    
    # TODO Need to check to see if we need to generate a thumbnail and generate it
    # Could we do this in .save() instead?
    # if talk.pdf_file:
        # _logger.debug("Talk '{}' has just been saved with PDF={}, checking to see if we should auto-generate a thumbnail".format(talk.title, talk.pdf_file.path))
        # thumbnail_res = 300
        # generate_and_save_thumbnail_from_pdf(talk, thumbnail_res)

    _logger.debug(f"Completed talk_post_save with sender={sender} and kwargs={kwargs}")

# Called automatically by Django after Talk is saved using Django's
# built-in signal dispatch functionality. We use this function to do some
# post-processong on the uploaded Talk data like auto-generating a thumbnail
# For more info on Django signal dispatch, see: https://docs.djangoproject.com/en/1.9/topics/signals/
@receiver(post_save, sender=Poster)
def poster_post_save(sender, **kwargs):
    # See: http://www.yaconiello.com/blog/auto-generating-pdf-covers/
    # http://stackoverflow.com/questions/1308386/programmatically-saving-image-to-django-imagefield

    # get the talk that was just saved and auto-generate a thumbnail
    poster = kwargs['instance']
    if poster.pdf_file:
        _logger.debug("Poster '{}' has just been saved with PDF={}, checking to see if we should auto-generate a thumbnail".format(poster.title, poster.pdf_file.path))
        thumbnail_res = 300
        generate_and_save_thumbnail_from_pdf(poster, thumbnail_res)

# Assumes that artifact is a models.Model type and has the following fields:
#  an ImageField called thumbnail
#  a FileField called pdf_file
def generate_and_save_thumbnail_from_pdf(artifact, thumbnail_resolution):

    # Get the thumbnail dir
    thumbnail_dir = os.path.normpath(os.path.normcase(os.path.join(settings.MEDIA_ROOT, artifact.thumbnail.field.upload_to)))

    # make sure this dir exists
    if not os.path.exists(thumbnail_dir):
        os.makedirs(thumbnail_dir)

    pdf_filename = os.path.basename(artifact.pdf_file.path)
    pdf_filename_no_ext = os.path.splitext(pdf_filename)[0]
    thumbnail_filename = "{}.{}".format(pdf_filename_no_ext, "jpg");
    thumbnail_path = os.path.join(thumbnail_dir, thumbnail_filename)

    _logger.debug("Checking for thumbnail at '{}', otherwise will auto-generate".format(thumbnail_path))

    # check to see if this is a new (or changed) file. This 'if condition' is super necessary
    # because otherwise we would enter an infinite loop given that we save the model again below
    if not artifact.thumbnail or artifact.thumbnail.name is None or \
                    os.path.normpath(os.path.normcase(artifact.thumbnail.path)) != os.path.normpath(os.path.normcase(thumbnail_path)):
        _logger.debug("Thumbnail does not exist, creating...")

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
        _logger.debug("No need to save, the thumbnail '{}' already exists!".format(thumbnail_path))