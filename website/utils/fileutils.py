from uuid import uuid4
import os
from django.utils.deconstruct import deconstructible
from django.conf import settings
import random

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


    print("settings.MEDIA_ROOT: ", settings.MEDIA_ROOT);

    # requires the volume mount from docker
    # Django doesn't like when we use absolute paths, so we need to get the relative path to the media folder
    local_media_folder = os.path.relpath(settings.MEDIA_ROOT)
    star_wars_path = os.path.join(local_media_folder, 'images', 'StarWarsFiguresFullSquare', starwars_side)
    print("star_wars_path: ", star_wars_path);

    all_images_in_dir = [f for f in os.listdir(star_wars_path) if is_image(f)]
    print("all_images_in_dir: ", all_images_in_dir);

    # Return a randoms single path
    return os.path.join(star_wars_path, random.choice(all_images_in_dir))