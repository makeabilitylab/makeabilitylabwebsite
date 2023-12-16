from django.core.management.base import BaseCommand
from website.models import Talk
import website.utils.fileutils as ml_fileutils
from django.conf import settings
import os
import logging

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "This is a one time use command to update talk filenames"

    def handle(self, *args, **options):
        _logger.debug("Running rename_talk_files.py to rename files to use new format. Should only be run once")
        
        # Go through all the talks and examine their filenames (for pdf and raw)
        # If they are not using Author_TalkTitle_VenueYear then rename
        for talk in Talk.objects.all():
            call_talk_save = False
            if talk.pdf_file and Command.does_artifact_need_to_be_renamed(talk, talk.pdf_file):
                new_filename_with_local_path = Command.generate_filename_with_local_path(talk, talk.pdf_file)
                new_filename = os.path.basename(new_filename_with_local_path)
                _logger.debug(f"For talk {talk}, renaming {talk.pdf_file.name} to {new_filename_with_local_path}")
                ml_fileutils.rename_artifact_on_filesystem(talk.pdf_file, new_filename)
                call_talk_save = True

            if talk.raw_file and Command.does_artifact_need_to_be_renamed(talk, talk.raw_file):
                new_filename_with_local_path = Command.generate_filename_with_local_path(talk, talk.raw_file)
                new_filename = os.path.basename(new_filename_with_local_path)
                _logger.debug(f"For talk {talk}, renaming {talk.raw_file.name} to {new_filename_with_local_path}")
                ml_fileutils.rename_artifact_on_filesystem(talk.raw_file, new_filename)
                call_talk_save = True

            if talk.thumbnail and Command.does_artifact_need_to_be_renamed(talk, talk.thumbnail):
                new_filename_with_local_path = Command.generate_filename_with_local_path(talk, talk.thumbnail)
                new_filename = os.path.basename(new_filename_with_local_path)
                _logger.debug(f"For talk {talk}, renaming {talk.thumbnail.name} to {new_filename_with_local_path}")
                ml_fileutils.rename_artifact_on_filesystem(talk.thumbnail, new_filename)
                call_talk_save = True
            
            if call_talk_save:
                talk.save()
                
        _logger.debug("Finished running rename_talk_files.py")

    @staticmethod
    def generate_filename_with_local_path(talk, artifact):
        """Returns a new filename with local path for this artifact
           talk: is a Talk model
           artifact: is a FileField
        """
        old_filename_with_local_path = artifact.name
        old_ext = os.path.splitext(old_filename_with_local_path)[1]
        new_filename = Talk.generate_filename(talk, old_ext)
        new_filename_with_local_path = os.path.join(
            os.path.dirname(old_filename_with_local_path), new_filename)
        
        return new_filename_with_local_path

    @staticmethod
    def does_artifact_need_to_be_renamed(talk, artifact):
        """Checks to see if the artifact needs to be renamed
           talk: is a Talk model
           artifact: is a FileField
        """
        old_filename_with_local_path = artifact.name
        new_filename_with_local_path = Command.generate_filename_with_local_path(talk, artifact)
        
        # if the filenames with local paths don't match, then need to rename
        return old_filename_with_local_path != new_filename_with_local_path
