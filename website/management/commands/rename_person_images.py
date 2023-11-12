from django.core.management.base import BaseCommand
from website.models import Person
from website.models.person import get_upload_to_for_person, get_upload_to_for_person_easter_egg
import website.utils.fileutils as ml_fileutils
from django.conf import settings
import os
import logging
from uuid import uuid4 # for generating unique filenames

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "This is a one time use command to update image and easter egg image filenames for people."

    def handle(self, *args, **options):
        _logger.debug("Running rename_person_images.py to rename files to use new format. Should only be run once")
        
        # Go through all the people and examine their image and easter egg filenames
        # If they are not using the format firstname_lastname.jpg and firstname_lastname_easter_egg.jpg,
        # then rename them to use that format
        for person in Person.objects.all():
            if person.image:
                # image.name returns the image filename with local path. It’s a path relative to your MEDIA_ROOT setting
                # image.path returns the absolute filesystem path to the file
                old_filename_with_local_path = person.image.name
                old_full_path = os.path.dirname(person.image.path)
                old_filename_with_full_path = person.image.path

                # Get the new filename for this person image. Make sure to force_unique to False because 
                # we want to check if we even *need* to rename this file (or if it's already been done)
                new_filename = os.path.basename(get_upload_to_for_person(person, old_filename_with_full_path, False))

                # Check if we need to rename it
                if os.path.basename(old_filename_with_full_path) != new_filename:

                    # Check if the old filename with full path exists
                    if not os.path.exists(old_filename_with_full_path):
                        _logger.debug(f"Could not rename person image for {person.get_full_name()} because the old filename does not exist: {old_filename_with_full_path}")
                    else: 
                        # Rename the file in the OS
                        new_filename_with_full_path = os.path.join(old_full_path, new_filename)
                        
                        # Check to see if that file already exists. If it does, make a new unique filename
                        while os.path.exists(new_filename_with_full_path):
                            _logger.debug(f"This filename with path exists {new_filename_with_full_path}, trying to generate a unique one")
                            
                            # The uuid4().hex generates a random UUID (Universally Unique Identifier), which is then appended to the filename. 
                            # This makes the probability of generating a duplicate filename extremely low. 
                            file_ext = os.path.splitext(os.path.basename(new_filename_with_full_path))[1]
                            new_filename_without_ext = os.path.splitext(os.path.basename(new_filename_with_full_path))[0]
                            new_filename_with_full_path = os.path.join(old_full_path, new_filename_without_ext + uuid4().hex + file_ext)


                        os.rename(old_filename_with_full_path, new_filename_with_full_path)
                        
                        # You cannot directly set the path attribute of an ImageField, so we set the name attribute instead
                        # which uses the local path
                        person.image.name = os.path.join(person.UPLOAD_DIR, os.path.basename(new_filename_with_full_path))
                        _logger.debug(f"Renamed person image from {old_filename_with_full_path} to {new_filename_with_full_path}")
                        _logger.debug(f"Old person.image.name={old_filename_with_local_path} and new={person.image.name}")
                        person.save()
                else:
                    _logger.debug(f"Skipping {person.get_full_name()} because {old_filename_with_full_path} did not need to be renamed")

            if person.easter_egg:
                old_ee_filename_with_local_path = person.easter_egg.name
                old_ee_filename_with_full_path = person.easter_egg.path
                old_ee_full_path = os.path.dirname(person.easter_egg.path)
                new_ee_filename = os.path.basename(get_upload_to_for_person_easter_egg(person, old_ee_filename_with_full_path, False))

                if os.path.basename(old_ee_filename_with_full_path) != new_ee_filename:
                    if not os.path.exists(old_ee_filename_with_full_path):
                        _logger.debug(f"Could not rename person easter egg image for {person.get_full_name()} because the old filename does not exist: {old_ee_filename_with_full_path}")
                    else: 
                        new_ee_filename_with_full_path = os.path.join(old_ee_full_path, new_ee_filename)

                         # Check to see if that file already exists. If it does, make a new unique filename
                        while os.path.exists(new_ee_filename_with_full_path):
                            _logger.debug(f"This filename with path exists {new_ee_filename_with_full_path}, trying to generate a unique one")
                            
                            # The uuid4().hex generates a random UUID (Universally Unique Identifier), which is then appended to the filename. 
                            # This makes the probability of generating a duplicate filename extremely low. 
                            file_ext = os.path.splitext(os.path.basename(new_ee_filename_with_full_path))[1]
                            new_filename_without_ext = os.path.splitext(os.path.basename(new_ee_filename_with_full_path))[0] 
                            new_ee_filename_with_full_path = os.path.join(old_full_path, new_ee_filename + uuid4().hex + file_ext)
                        
                        os.rename(old_ee_filename_with_full_path, new_ee_filename_with_full_path)
                        person.easter_egg.name = os.path.join(person.UPLOAD_DIR, os.path.basename(new_ee_filename_with_full_path))
                        _logger.debug(f"Renamed person easter egg image from {old_ee_filename_with_full_path} to {new_ee_filename_with_full_path}")
                        _logger.debug(f"Old person.image.name={old_ee_filename_with_local_path} and new={person.easter_egg.name}")
                        person.save()
                else:
                    _logger.debug(f"Skipping {person.get_full_name()}'s easter egg rename because {old_ee_filename_with_full_path} did not need to be renamed")
                        
            

        # Now remove all the old thumbnails and unused person files. Don't worry, the thumbnails will get auto-generated again on demand
        person_image_dir = os.path.normpath(os.path.normcase(os.path.join(settings.MEDIA_ROOT, Person.UPLOAD_DIR)))
        person_image_files_with_path = ml_fileutils.get_files_in_directory(person_image_dir)
        total_file_count = len(person_image_files_with_path)
        _logger.debug(f"{len(person_image_files_with_path)} person image files (including auto-generated thumbnails) on filesystem")
        map_image_filenames_to_full_paths_on_filesystem = self.get_map_basename_to_full_path(person_image_files_with_path)

        for person in Person.objects.all():
            if person.image:
                if os.path.basename(person.image.path) in map_image_filenames_to_full_paths_on_filesystem:
                    _logger.debug(f"For person {person.get_full_name()}, keeping file with person.image.path: {person.image.path}")
                    del map_image_filenames_to_full_paths_on_filesystem[os.path.basename(person.image.path)]
            if person.easter_egg:    
                if os.path.basename(person.easter_egg.path) in map_image_filenames_to_full_paths_on_filesystem:
                    _logger.debug(f"For person {person.get_full_name()}, keeping file with person.easter_egg.path: {person.easter_egg.path}")
                    del map_image_filenames_to_full_paths_on_filesystem[os.path.basename(person.easter_egg.path)]

        remaining_file_count = len(map_image_filenames_to_full_paths_on_filesystem)
        _logger.debug(f"We are set to delete {len(map_image_filenames_to_full_paths_on_filesystem)} files in {person_image_dir}")
        _logger.debug(f"This is {remaining_file_count/total_file_count*100:0.1f}% of the total {total_file_count} files in {person_image_dir}")
        for filename_with_path in map_image_filenames_to_full_paths_on_filesystem.values():
            _logger.debug(f"Deleting {filename_with_path}")
            os.remove(filename_with_path)   

        _logger.debug("Finished running rename_person_images.py")


    def get_map_basename_to_full_path(self, files):
        map_filename_to_full_path = dict()
        for file_with_path in files:
            filename = os.path.basename(file_with_path)
            map_filename_to_full_path[filename] = file_with_path
        return map_filename_to_full_path