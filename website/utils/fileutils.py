from uuid import uuid4
import os
from django.utils.deconstruct import deconstructible
from django.conf import settings
import random
import logging
from django.utils.text import get_valid_filename

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)


# By default, Django does not auto-rename a file to guarantee its uniqueness; this code
# provides that functionality. See: http://stackoverflow.com/questions/15140942/django-imagefield-change-file-name-on-upload
@deconstructible # Class decorator that allow the decorated class to be serialized by the migrations subsystem.
class UniquePathAndRename(object):

    def __init__(self, sub_path, appendUniqueString=False):
        self.path = sub_path

        # if True, we will append the unique string rather than replace
        self.append_unique_string = appendUniqueString

    def __call__(self, instance, filename):
        ext = filename.split('.')[-1]

        # set filename as random string
        filenameNoExt = filename.split('.')[0]
        if self.append_unique_string:
            filenameNoExt = filenameNoExt + uuid4().hex
        else:
            filenameNoExt = uuid4().hex

        filename = '{}.{}'.format(filenameNoExt, ext)

        # return the whole path to the file
        return os.path.join(self.path, filename)

# See: https://django-ckeditor.readthedocs.io/en/latest/#required-for-using-widget-with-file-upload
def get_ckeditor_image_filename(filename):
    """Returns file name for CKEditor image uploads"""
    return filename.upper()

def is_image(filename):
    """true if the filename's extension is in the content-type lookup"""
    ext2conttype = {"jpg": "image/jpeg",
                    "jpeg": "image/jpeg",
                    "png": "image/png",
                    "gif": "image/gif"}
    
    filename = filename.lower()
    return filename[filename.rfind(".") + 1:] in ext2conttype

def get_path_to_random_starwars_image(starwars_side = 'Rebels'):
    """Gets a random star wars image path to assign"""
    
    if not starwars_side or starwars_side not in ['Rebels', 'Neither', 'DarkSide', 'Unfiled']:
        starwars_side = 'Rebels'

    #print("settings.MEDIA_ROOT: ", settings.MEDIA_ROOT);

    # requires the volume mount from docker
    # Django doesn't like when we use absolute paths, so we need to get the relative path to the media folder
    local_media_folder = os.path.relpath(settings.MEDIA_ROOT)
    star_wars_path = os.path.join(local_media_folder, 'images', 'StarWarsFiguresFullSquare', starwars_side)
    # print("star_wars_path: ", star_wars_path);

    all_images_in_dir = [f for f in os.listdir(star_wars_path) if is_image(f)]
    # print("all_images_in_dir: ", all_images_in_dir);

    # Return a randoms single path
    return os.path.join(star_wars_path, random.choice(all_images_in_dir))

def get_files_in_directory(dir_path):
    """Returns a list of files in the given directory"""
    return [os.path.join(dir_path, f) for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))]

def get_filename_without_ext_for_artifact(last_name, title, forum_name, date):
    """Generates a filename from the provided content"""

    last_name = last_name.replace(" ", "")
    year = date.year
    title = ''.join(x for x in title.title() if not x.isspace())
    title = ''.join(e for e in title if e.isalnum())

    forum_name = forum_name.replace(" ", "")

    # Convert metadata into a filename
    new_filename_no_ext = last_name + '_' + title + '_' + forum_name + str(year)
    return get_valid_filename(new_filename_no_ext)
    

def ensure_filename_is_unique(filename_with_full_path):
    """Will return a filename with full path that is guaranteed to be unique"""
    while os.path.exists(filename_with_full_path):
        _logger.debug(f"This filename with path exists {filename_with_full_path}, trying to generate a unique one")

        # The uuid4().hex generates a random UUID (Universally Unique Identifier), which is then appended to the filename. 
        # This makes the probability of generating a duplicate filename extremely low. 
        full_path = os.path.dirname(filename_with_full_path)
        file_ext = os.path.splitext(os.path.basename(filename_with_full_path))[1]
        new_filename_without_ext = os.path.splitext(os.path.basename(filename_with_full_path))[0]
        filename_with_full_path = os.path.join(full_path, new_filename_without_ext + "-" + uuid4().hex + file_ext)  
    
    # Returns a guaranteed to be unique filename (with path)
    return filename_with_full_path

def rename(artifact, new_filename_no_ext):
    """Renames the artifact in the database and filesystem"""

    old_filename_with_full_path = artifact.path
    old_local_path = os.path.dirname(artifact.name)
    old_full_path = os.path.dirname(old_filename_with_full_path)
    old_filename_ext = os.path.splitext(old_filename_with_full_path)[1]
    
    # Make the new filename with the extension
    new_filename = new_filename_no_ext + old_filename_ext

    # Use Django helper function to ensure a clean filename
    new_filename = get_valid_filename(new_filename)

    # Add in the media directory
    new_filename_with_full_path = os.path.join(old_full_path, new_filename)
    new_filename_with_full_path = ensure_filename_is_unique(new_filename_with_full_path)

    # Change the pdf_file path to point to the renamed file
    artifact.name = os.path.join(old_local_path, os.path.basename(new_filename_with_full_path))

    # Actually rename the existing file (aka initial_path) but only if it exists (it should!)
    if os.path.exists(old_filename_with_full_path):
        os.rename(old_filename_with_full_path, new_filename_with_full_path)
        _logger.debug(f"Renamed {old_filename_with_full_path} to {new_filename_with_full_path}")
        return new_filename_with_full_path
    else:
        _logger.error(f'The file {old_filename_with_full_path} does not exist and cannot be renamed to {new_filename_with_full_path}')
        return None