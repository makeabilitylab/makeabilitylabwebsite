from django.db.models.signals import post_save
from django.dispatch import receiver
from website.models import Talk, Publication, Poster
from wand.image import Image
from django.conf import settings
import os
from django.core.files import File

@receiver(post_save, sender=Publication)
def my_handler(sender, **kwargs):
    # See: http://www.yaconiello.com/blog/auto-generating-pdf-covers/
    # http://stackoverflow.com/questions/1308386/programmatically-saving-image-to-django-imagefield

    # get the publication that was just saved
    pub = kwargs['instance']
    print("Publication '{}' has just been saved with PDF={}, checking to see if we should auto-generate a thumbnail".format(pub.title, pub.pdf_file.path))
    thumbnail_res = 300
    generate_and_save_thumbnail_from_pdf(pub, thumbnail_res)

@receiver(post_save, sender=Talk)
def my_handler(sender, **kwargs):
    # See: http://www.yaconiello.com/blog/auto-generating-pdf-covers/
    # http://stackoverflow.com/questions/1308386/programmatically-saving-image-to-django-imagefield

    # # get the talk that was just saved
    talk = kwargs['instance']
    print("Talk '{}' has just been saved with PDF={}, checking to see if we should auto-generate a thumbnail".format(talk.title, talk.pdf_file.path))
    thumbnail_res = 300
    generate_and_save_thumbnail_from_pdf(talk, thumbnail_res)

    #
    # # thumbnailPath = os.path.join(talk.thumbnail.storage.base_location, talk.thumbnail.field.upload_to)
    # # thumbnail_dir = os.path.dirname(talk.pdf_file.path)
    # thumbnail_dir = os.path.normpath(os.path.normcase(os.path.join(settings.MEDIA_ROOT, talk.thumbnail.field.upload_to)))
    #
    # # make sure this dir exists
    # if not os.path.exists(thumbnail_dir):
    #     os.makedirs(thumbnail_dir)
    #
    # pdf_filename = os.path.basename(talk.pdf_file.path)
    # pdf_filename_no_extension = os.path.splitext(pdf_filename)[0]
    # thumbnail_filename = "{}.{}".format(pdf_filename_no_extension, "jpg");
    # thumbnail_path = os.path.join(thumbnail_dir, thumbnail_filename)
    #
    # # check to see if this is a new (or changed) file. This 'if condition' is super necessary
    # # because otherwise we would enter an infinite loop given that we save the model again below
    # if talk.thumbnail.name is None or \
    #                 os.path.normpath(os.path.normcase(talk.thumbnail.path)) != os.path.normpath(os.path.normcase(thumbnail_path)):
    #     with Image(filename="{}[0]".format(talk.pdf_file.path), resolution=thumbnail_res) as img:
    #          img.save(filename=thumbnail_path)
    #
    #     # talk.thumbnail = thumbnail_path
    #     testpath = os.path.join(talk.thumbnail.field.upload_to, thumbnail_filename)
    #     talk.thumbnail = testpath
    #     # talk.thumbnail.save(thumbnail_dir, File(open(thumbnail_path)))
    #     talk.save()
    # else:
    #     print("No need to save!")

@receiver(post_save, sender=Poster)
def my_handler(sender, **kwargs):
    # See: http://www.yaconiello.com/blog/auto-generating-pdf-covers/
    # http://stackoverflow.com/questions/1308386/programmatically-saving-image-to-django-imagefield

    # get the poster that was just saved
    poster = kwargs['instance']
    print("Poster '{}' has just been saved with PDF={}, checking to see if we should auto-generate a thumbnail".format(poster.title, poster.pdf_file.path))
    thumbnail_res = 300
    generate_and_save_thumbnail_from_pdf(poster, thumbnail_res)

# Assumes that artifact is a models.Model type and has the following fields:
#  an ImageField called thumbnail
#  a FileField called pdf_file
def generate_and_save_thumbnail_from_pdf(artifact, thumbnail_resolution):
    thumbnail_dir = os.path.normpath(os.path.normcase(os.path.join(settings.MEDIA_ROOT, artifact.thumbnail.field.upload_to)))

    # make sure this dir exists
    if not os.path.exists(thumbnail_dir):
        os.makedirs(thumbnail_dir)

    pdf_filename = os.path.basename(artifact.pdf_file.path)
    pdf_filename_no_extension = os.path.splitext(pdf_filename)[0]
    thumbnail_filename = "{}.{}".format(pdf_filename_no_extension, "jpg");
    thumbnail_path = os.path.join(thumbnail_dir, thumbnail_filename)

    # check to see if this is a new (or changed) file. This 'if condition' is super necessary
    # because otherwise we would enter an infinite loop given that we save the model again below
    if artifact.thumbnail.name is None or \
                    os.path.normpath(os.path.normcase(artifact.thumbnail.path)) != os.path.normpath(os.path.normcase(thumbnail_path)):
        with Image(filename="{}[0]".format(artifact.pdf_file.path), resolution=thumbnail_resolution) as img:
             img.save(filename=thumbnail_path)

        # talk.thumbnail = thumbnail_path
        relative_thumbnail_path = os.path.join(artifact.thumbnail.field.upload_to, thumbnail_filename)
        artifact.thumbnail = relative_thumbnail_path

        artifact.save()
    else:
        print("No need to save, the thumbnail '{}' already exists!".format(thumbnail_path))