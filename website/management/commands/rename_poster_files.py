from django.core.management.base import BaseCommand
from website.models import Poster
import website.utils.fileutils as ml_fileutils
from django.conf import settings
import os
import logging

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "This is a one time use command to update poster filenames"

    def handle(self, *args, **options):
        _logger.debug("Running rename_poster_files.py to rename files to use new format. Should only be run once")
        
        # Go through all the posters and examine their filenames (for both pdf and raw)
        # If they are not using Author_PosterTitle_VenueYear then rename
        for poster in Poster.objects.all():
            if poster.pdf_file and Command.does_artifact_need_to_be_renamed(poster, poster.pdf_file):
                new_filename_with_local_path = Command.generate_filename_with_local_path(poster, poster.pdf_file)
                new_filename = os.path.basename(new_filename_with_local_path)
                _logger.debug(f"For poster {poster}, renaming {poster.pdf_file.name} to {new_filename_with_local_path}")
                ml_fileutils.rename_artifact_in_db_and_filesystem(poster, poster.pdf_file, new_filename)

            if poster.raw_file and Command.does_artifact_need_to_be_renamed(poster, poster.raw_file):
                new_filename_with_local_path = Command.generate_filename_with_local_path(poster, poster.raw_file)
                new_filename = os.path.basename(new_filename_with_local_path)
                _logger.debug(f"For poster {poster}, renaming {poster.raw_file.name} to {new_filename_with_local_path}")
                ml_fileutils.rename_artifact_in_db_and_filesystem(poster, poster.raw_file, new_filename)
                
        _logger.debug("Finished running rename_poster_files.py")

    @staticmethod
    def generate_filename_with_local_path(poster, artifact):
        """Returns a new filename with local path for this artifact"""
        old_filename_with_local_path = artifact.name
        old_ext = os.path.splitext(old_filename_with_local_path)[1]
        new_filename = Poster.generate_filename(poster, old_ext)
        new_filename_with_local_path = os.path.join(
            os.path.dirname(old_filename_with_local_path), new_filename)
        
        return new_filename_with_local_path

    @staticmethod
    def does_artifact_need_to_be_renamed(poster, artifact):
        """Checks to see if the artifact needs to be renamed"""
        old_filename_with_local_path = artifact.name
        new_filename_with_local_path = Command.generate_filename_with_local_path(poster, artifact)
        
        # if the filenames with local paths don't match, then need to rename
        return old_filename_with_local_path != new_filename_with_local_path
