from django.core.management.base import BaseCommand, CommandError
from website.models import Publication
from django.conf import settings
import os
import glob

import logging

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

class Command(BaseCommand):

    help = 'Looks for old pub files no longer used'

    def handle(self, *args, **options):

        # Get all of the PDF publication files in the filesystem
        pub_dir = os.path.normpath(os.path.normcase(os.path.join(settings.MEDIA_ROOT, Publication.UPLOAD_DIR)))
        pdf_files_on_filesystem_with_path = glob.glob(os.path.join(pub_dir,"*.pdf"))
        _logger.debug("{} PDF publication files on filesystem".format(len(pdf_files_on_filesystem_with_path)));
        map_pdf_filename_to_full_path_on_filesystem = self.get_map_basename_to_full_path(
            pdf_files_on_filesystem_with_path)

        # Get all of the publication thumbnail files in the filesystem
        pub_thumbnail_dir = os.path.normpath(os.path.normcase(os.path.join(settings.MEDIA_ROOT, Publication.THUMBNAIL_DIR)))
        pub_thumbnail_files_on_filesystem_with_path = glob.glob(os.path.join(pub_thumbnail_dir,"*.jpg"))
        _logger.debug("{} publication thumbnail files on filesystem".format(len(pub_thumbnail_files_on_filesystem_with_path)));
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
        
        _logger.debug("{} non-easy-thumbnail thumbnails on filesystem".format(len(map_pub_thumbnail_to_full_path_on_filesystem)));

        # Go through pubs and thumbnails in database and remove entries from
        # our filesystem dictionaries (we will delete whatever is left over in these dicts)
        map_pub_filename_to_full_path_in_database = dict()
        map_thumbnail_filename_to_full_path_in_database = dict()
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
            _logger.debug("Deleted {} unused pubs ({} bytes total)".format(num_files_deleted, bytes_deleted)); 
        else:
            _logger.debug("There are no unused pub thumbnails to delete")

        print("\n------------")
        print("Make sure to also run 'python manage.py thumbnail_cleanup', which will execute easy-thumbnail's cleanup")
        print("See: https://github.com/SmileyChris/easy-thumbnails/blob/master/easy_thumbnails/management/commands/thumbnail_cleanup.py");

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