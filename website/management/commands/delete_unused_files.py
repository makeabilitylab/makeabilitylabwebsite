from django.core.management.base import BaseCommand, CommandError
from website.models import Publication, Talk, Poster
from django.conf import settings
import os
import glob

import logging

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

class Command(BaseCommand):

    help = 'Looks for old publication, talk, and poster files and thumbnails no longer used'

    def handle(self, *args, **options):
        _logger.debug("Running delete_unused_files.py command to search for and delete unused files in filesystem")
        self.delete_unused_pubs()
        self.delete_unused_talks()
        self.delete_unused_posters()

        print("\n------------")
        print("Make sure to also run 'python manage.py thumbnail_cleanup', which will execute easy-thumbnail's cleanup")
        print("See: https://github.com/SmileyChris/easy-thumbnails/blob/master/easy_thumbnails/management/commands/thumbnail_cleanup.py")

    def delete_unused_posters(self):
        # Get all of the PDF poster files in the filesystem
        poster_dir = os.path.normpath(os.path.normcase(os.path.join(settings.MEDIA_ROOT, Poster.UPLOAD_DIR)))
        poster_pdf_files_on_filesystem_with_path = glob.glob(os.path.join(poster_dir,"*.pdf"))
        _logger.debug("{} PDF poster files on filesystem".format(len(poster_pdf_files_on_filesystem_with_path)))
        map_poster_pdf_filename_to_full_path_on_filesystem = self.get_map_basename_to_full_path(
            poster_pdf_files_on_filesystem_with_path)

        # Get all of the raw poster files in the filesystem
        raw_poster_files_on_filesystem_with_path = glob.glob(os.path.join(poster_dir,"*.pptx")) +\
            glob.glob(os.path.join(poster_dir,"*.key")) + glob.glob(os.path.join(poster_dir,"*.ai"))
        _logger.debug("{} raw poster files on filesystem".format(len(raw_poster_files_on_filesystem_with_path)))
        map_raw_poster_filename_to_full_path_on_filesystem = self.get_map_basename_to_full_path(
            raw_poster_files_on_filesystem_with_path)

        # Get all of the publication thumbnail files in the filesystem
        poster_thumbnail_dir = os.path.normpath(os.path.normcase(os.path.join(settings.MEDIA_ROOT, Poster.THUMBNAIL_DIR)))
        poster_thumbnail_files_on_filesystem_with_path = glob.glob(os.path.join(poster_thumbnail_dir,"*.jpg"))
        _logger.debug("{} poster thumbnail files on filesystem".format(len(poster_thumbnail_files_on_filesystem_with_path)))
        map_poster_thumbnail_to_full_path_on_filesystem = self.get_map_basename_to_full_path(
            poster_thumbnail_files_on_filesystem_with_path)

        # remove easy-thumbnail thumbnails
        poster_thumbnail_filenames = list(map_poster_thumbnail_to_full_path_on_filesystem.keys())
        for poster_thumbnail_filename in poster_thumbnail_filenames:
            if '_detail' in poster_thumbnail_filename:
                del map_poster_thumbnail_to_full_path_on_filesystem[poster_thumbnail_filename]
        
        _logger.debug("{} non-easy-thumbnail poster thumbnails on filesystem".format(len(map_poster_thumbnail_to_full_path_on_filesystem)))

        # Go through talks and thumbnails in database and remove entries from
        # our filesystem dictionaries (we will delete whatever is left over in these dicts)
        for poster in Poster.objects.all():

            # If this pdf exists in the filesystem, keep it there (don't delete it)
            if poster.pdf_file:
                poster_pdf_filename = os.path.basename(poster.pdf_file.path)
                if poster_pdf_filename in map_poster_pdf_filename_to_full_path_on_filesystem:
                    del map_poster_pdf_filename_to_full_path_on_filesystem[poster_pdf_filename]

            # If this pptx exists in the filesystem, keep it there (don't delete it)
            if poster.raw_file:
                raw_poster_filename = os.path.basename(poster.raw_file.path)
                if raw_poster_filename in map_raw_poster_filename_to_full_path_on_filesystem:
                    del map_raw_poster_filename_to_full_path_on_filesystem[raw_poster_filename]
  
            # If this thumbnail exists in the filesystem, keep it there (don't delete it)
            if poster.thumbnail:
                poster_thumbnail_filename = os.path.basename(poster.thumbnail.path)
                if poster_thumbnail_filename in map_poster_thumbnail_to_full_path_on_filesystem:
                    del map_poster_thumbnail_to_full_path_on_filesystem[poster_thumbnail_filename]

        if len(map_poster_pdf_filename_to_full_path_on_filesystem) > 0:
            _logger.debug("Set to delete {} unused poster PDFs".format(len(map_poster_pdf_filename_to_full_path_on_filesystem)))  
            (num_files_deleted, bytes_deleted) = self.delete_unused_files(map_poster_pdf_filename_to_full_path_on_filesystem.values())
            _logger.debug("Deleted {} unused poster PDFs ({} bytes total)".format(num_files_deleted, bytes_deleted))
        else:
            _logger.debug("There are no unused poster PDFs to delete")

        if len(map_raw_poster_filename_to_full_path_on_filesystem) > 0:
            _logger.debug("Set to delete {} unused poster .pptx, .ai, .key".format(len(map_raw_poster_filename_to_full_path_on_filesystem)))  
            (num_files_deleted, bytes_deleted) = self.delete_unused_files(map_raw_poster_filename_to_full_path_on_filesystem.values())
            _logger.debug("Deleted {} unused poster .pptx, .ai, .key files ({} bytes total)".format(num_files_deleted, bytes_deleted))
        else:
            _logger.debug("There are no unused raw poster files to delete")


        if len(map_poster_thumbnail_to_full_path_on_filesystem) > 0:
            _logger.debug("Set to delete {} unused poster thumbnails".format(len(map_poster_thumbnail_to_full_path_on_filesystem)))
            (num_files_deleted, bytes_deleted) = self.delete_unused_files(map_poster_thumbnail_to_full_path_on_filesystem.values())   
            _logger.debug("Deleted {} unused poster thumbnails ({} bytes total)".format(num_files_deleted, bytes_deleted)) 
        else:
            _logger.debug("There are no unused poster thumbnails to delete")

    def delete_unused_talks(self):
        # Get all of the PDF talk files in the filesystem
        talk_dir = os.path.normpath(os.path.normcase(os.path.join(settings.MEDIA_ROOT, Talk.UPLOAD_DIR)))
        talk_pdf_files_on_filesystem_with_path = glob.glob(os.path.join(talk_dir,"*.pdf"))
        _logger.debug("{} PDF talk files on filesystem".format(len(talk_pdf_files_on_filesystem_with_path)))
        map_talk_pdf_filename_to_full_path_on_filesystem = self.get_map_basename_to_full_path(
            talk_pdf_files_on_filesystem_with_path)

        # Get all of the PowerPoint and keynote talk files in the filesystem
        talk_pptx_files_on_filesystem_with_path = glob.glob(os.path.join(talk_dir,"*.pptx")) +\
            glob.glob(os.path.join(talk_dir,"*.key"))
        _logger.debug("{} PPTX talk files on filesystem".format(len(talk_pptx_files_on_filesystem_with_path)))
        map_talk_pptx_filename_to_full_path_on_filesystem = self.get_map_basename_to_full_path(
            talk_pptx_files_on_filesystem_with_path)

        # Get all of the publication thumbnail files in the filesystem
        talk_thumbnail_dir = os.path.normpath(os.path.normcase(os.path.join(settings.MEDIA_ROOT, Talk.THUMBNAIL_DIR)))
        talk_thumbnail_files_on_filesystem_with_path = glob.glob(os.path.join(talk_thumbnail_dir,"*.jpg"))
        _logger.debug("{} talk thumbnail files on filesystem".format(len(talk_thumbnail_files_on_filesystem_with_path)))
        map_talk_thumbnail_to_full_path_on_filesystem = self.get_map_basename_to_full_path(
            talk_thumbnail_files_on_filesystem_with_path)

        # remove easy-thumbnail thumbnails
        talk_thumbnail_filenames = list(map_talk_thumbnail_to_full_path_on_filesystem.keys())
        for talk_thumbnail_filename in talk_thumbnail_filenames:
            if '_detail' in talk_thumbnail_filename:
                del map_talk_thumbnail_to_full_path_on_filesystem[talk_thumbnail_filename]
        
        _logger.debug("{} non-easy-thumbnail talk thumbnails on filesystem".format(len(map_talk_thumbnail_to_full_path_on_filesystem)))

        # Go through talks and thumbnails in database and remove entries from
        # our filesystem dictionaries (we will delete whatever is left over in these dicts)
        for talk in Talk.objects.all():

            # If this pdf exists in the filesystem, keep it there (don't delete it)
            talk_pdf_filename = os.path.basename(talk.pdf_file.path)
            if talk_pdf_filename in map_talk_pdf_filename_to_full_path_on_filesystem:
                del map_talk_pdf_filename_to_full_path_on_filesystem[talk_pdf_filename]

            # If this pptx exists in the filesystem, keep it there (don't delete it)
            if talk.raw_file:
                talk_pptx_filename = os.path.basename(talk.raw_file.path)
                if talk_pptx_filename in map_talk_pptx_filename_to_full_path_on_filesystem:
                    del map_talk_pptx_filename_to_full_path_on_filesystem[talk_pptx_filename]
  
            # If this thumbnail exists in the filesystem, keep it there (don't delete it)
            if talk.thumbnail:
                talk_thumbnail_filename = os.path.basename(talk.thumbnail.path)
                if talk_thumbnail_filename in map_talk_thumbnail_to_full_path_on_filesystem:
                    del map_talk_thumbnail_to_full_path_on_filesystem[talk_thumbnail_filename]

        if len(map_talk_pdf_filename_to_full_path_on_filesystem) > 0:
            _logger.debug("Set to delete {} unused talk PDFs".format(len(map_talk_pdf_filename_to_full_path_on_filesystem)))  
            (num_files_deleted, bytes_deleted) = self.delete_unused_files(map_talk_pdf_filename_to_full_path_on_filesystem.values())
            _logger.debug("Deleted {} unused talk PDFs ({} bytes total)".format(num_files_deleted, bytes_deleted))
        else:
            _logger.debug("There are no unused talk PDFs to delete")

        if len(map_talk_pptx_filename_to_full_path_on_filesystem) > 0:
            _logger.debug("Set to delete {} unused talk PPTXs".format(len(map_talk_pptx_filename_to_full_path_on_filesystem)))  
            (num_files_deleted, bytes_deleted) = self.delete_unused_files(map_talk_pptx_filename_to_full_path_on_filesystem.values())
            _logger.debug("Deleted {} unused talk PPTXs ({} bytes total)".format(num_files_deleted, bytes_deleted))
        else:
            _logger.debug("There are no unused talk PPTXs to delete")


        if len(map_talk_thumbnail_to_full_path_on_filesystem) > 0:
            _logger.debug("Set to delete {} unused talk thumbnails".format(len(map_talk_thumbnail_to_full_path_on_filesystem)))
            (num_files_deleted, bytes_deleted) = self.delete_unused_files(map_talk_thumbnail_to_full_path_on_filesystem.values())   
            _logger.debug("Deleted {} unused talk thumbnails ({} bytes total)".format(num_files_deleted, bytes_deleted)) 
        else:
            _logger.debug("There are no unused talk thumbnails to delete")

    def delete_unused_pubs(self):
        # Get all of the PDF publication files in the filesystem
        pub_dir = os.path.normpath(os.path.normcase(os.path.join(settings.MEDIA_ROOT, Publication.UPLOAD_DIR)))
        pdf_files_on_filesystem_with_path = glob.glob(os.path.join(pub_dir,"*.pdf"))
        _logger.debug("{} PDF publication files on filesystem".format(len(pdf_files_on_filesystem_with_path)))
        map_pdf_filename_to_full_path_on_filesystem = self.get_map_basename_to_full_path(
            pdf_files_on_filesystem_with_path)

        # Get all of the publication thumbnail files in the filesystem
        pub_thumbnail_dir = os.path.normpath(os.path.normcase(os.path.join(settings.MEDIA_ROOT, Publication.THUMBNAIL_DIR)))
        pub_thumbnail_files_on_filesystem_with_path = glob.glob(os.path.join(pub_thumbnail_dir,"*.jpg"))
        _logger.debug("{} publication thumbnail files on filesystem".format(len(pub_thumbnail_files_on_filesystem_with_path)))
        map_pub_thumbnail_to_full_path_on_filesystem = self.get_map_basename_to_full_path(
            pub_thumbnail_files_on_filesystem_with_path)
        
        # The plug "easy-thumbnails" https://easy-thumbnails.readthedocs.io/en/latest/usage/
        # has auto-generates optimized thumbnails for web display and puts 'detail' in the filename
        # So, for example: "Froehlich_ThisIsATestPublication_CHI2022.jpg" might have an auto-generated
        # thumbnail as "Froehlich_ThisIsATestPublication_CHI2022.jpg.300x0_q85_detail.jpg"
        # 
        # easy-thumbnails has its own cleanup routine, so we don't want to deal with these files
        # We filter them out below by looking for the string `_detail`
        pub_thumbnail_filenames = list(map_pub_thumbnail_to_full_path_on_filesystem.keys())
        for pub_thumbnail_filename in pub_thumbnail_filenames:
            if '_detail' in pub_thumbnail_filename:
                del map_pub_thumbnail_to_full_path_on_filesystem[pub_thumbnail_filename]
        
        _logger.debug("{} non-easy-thumbnail pub thumbnails on filesystem".format(len(map_pub_thumbnail_to_full_path_on_filesystem)))

        # Go through pubs and thumbnails in database and remove entries from
        # our filesystem dictionaries (we will delete whatever is left over in these dicts)
        for pub in Publication.objects.all():

            pub_pdf_filename = os.path.basename(pub.pdf_file.path)

            # If this pdf exists in the filesystem, keep it there (don't delete it)
            if pub_pdf_filename in map_pdf_filename_to_full_path_on_filesystem:
                del map_pdf_filename_to_full_path_on_filesystem[pub_pdf_filename]
  
            # If this thumbnail exists in the filesystem, keep it there (don't delete it)
            pub_thumbnail_filename = os.path.basename(pub.thumbnail.path)
            if pub_thumbnail_filename in map_pub_thumbnail_to_full_path_on_filesystem:
                del map_pub_thumbnail_to_full_path_on_filesystem[pub_thumbnail_filename]

        if len(map_pdf_filename_to_full_path_on_filesystem) > 0:
            _logger.debug("Set to delete {} unused pub PDFs".format(len(map_pdf_filename_to_full_path_on_filesystem)))  
            (num_files_deleted, bytes_deleted) = self.delete_unused_files(map_pdf_filename_to_full_path_on_filesystem.values())
            _logger.debug("Deleted {} unused pubs ({} bytes total)".format(num_files_deleted, bytes_deleted))
        else:
            _logger.debug("There are no unused pub PDFs to delete")


        if len(map_pub_thumbnail_to_full_path_on_filesystem) > 0:
            _logger.debug("Set to delete {} unused pub thumbnails".format(len(map_pub_thumbnail_to_full_path_on_filesystem)))
            (num_files_deleted, bytes_deleted) = self.delete_unused_files(map_pub_thumbnail_to_full_path_on_filesystem.values())   
            _logger.debug("Deleted {} unused pub thumbnails ({} bytes total)".format(num_files_deleted, bytes_deleted)) 
        else:
            _logger.debug("There are no unused pub thumbnails to delete")

    def delete_unused_files(self, files):
        bytes_deleted = 0
        num_files_deleted = 0     
        for filename_with_path_to_delete in files:
            _logger.debug("Attempting to delete unused file: {}".format(filename_with_path_to_delete))
            bytes_deleted += os.path.getsize(filename_with_path_to_delete)
            os.remove(filename_with_path_to_delete)
            num_files_deleted += 1
        
        return (num_files_deleted, bytes_deleted)

    def get_map_basename_to_full_path(self, files):
        map_filename_to_full_path = dict()
        for file_with_path in files:
            filename = os.path.basename(file_with_path)
            map_filename_to_full_path[filename] = file_with_path
        return map_filename_to_full_path


# Running thumbnail_cleanup
# apache@31c0a0c7ed35:/code$ python manage.py thumbnail_cleanup
# Source not present: /code/media/publications/images/Froehlich_ThisIsAPubThatIAmGoingToDelete_ASSETS2021.jpg
# Deleting thumbnail: /code/media/publications/images/Froehlich_ThisIsAPubThatIAmGoingToDelete_ASSETS2021.jpg.300x0_q85_detail.jpg
# 2022-10-31 15:56 -------------------------------
# Sources checked:                               4
# Source references deleted from DB:             1
# Thumbnails deleted from disk:                  1
# (Completed in 0 seconds)