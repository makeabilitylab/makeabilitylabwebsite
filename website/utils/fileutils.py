from uuid import uuid4
import os
from django.utils.deconstruct import deconstructible
from django.conf import settings
import random
import logging
from django.utils.text import get_valid_filename
import time # for generating unique filenames
from wand.image import Image, Color # for creating thumbnails
from wand.exceptions import WandException# for creating thumbnails
from pypdf import PdfReader # for counting PDF pages
from pypdf.errors import PdfReadError # for counting PDF pages

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

# The Star Wars LEGO figures that seed a Person's default headshot / easter-egg
# image live under media/images/StarWarsFiguresFullSquare/<side>/. 'Rebels' is
# the canonical set used for easter eggs (see Person.easter_egg).
STARWARS_SIDES = ['Rebels', 'Neither', 'DarkSide', 'Unfiled']
STARWARS_SUBDIR = ('images', 'StarWarsFiguresFullSquare')


def _normalize_starwars_side(starwars_side):
    """Coerce an arbitrary side to a known one, defaulting to 'Rebels'."""
    if not starwars_side or starwars_side not in STARWARS_SIDES:
        return 'Rebels'
    return starwars_side


def get_starwars_image_dir(starwars_side='Rebels'):
    """Returns the on-disk directory (relative to cwd) for a Star Wars side.

    Django dislikes absolute paths for FileField assignment, so we return a
    path relative to MEDIA_ROOT's relative form (matches existing usage).
    """
    starwars_side = _normalize_starwars_side(starwars_side)
    # requires the volume mount from docker
    local_media_folder = os.path.relpath(settings.MEDIA_ROOT)
    return os.path.join(local_media_folder, *STARWARS_SUBDIR, starwars_side)


def list_starwars_images(starwars_side='Rebels'):
    """Returns a sorted list of Star Wars image *basenames* for the given side.

    This is the single source of truth for the available figures: both the
    random default picker (:func:`get_path_to_random_starwars_image`) and the
    admin easter-egg picker (which lets editors preview/shuffle a figure before
    the first save, see #1304) build on it.

    Example:
        >>> list_starwars_images('Rebels')[:2]
        ['300px-Ani-helmet.jpg', '540px-Logray.jpg']
    """
    star_wars_path = get_starwars_image_dir(starwars_side)
    return sorted(f for f in os.listdir(star_wars_path) if is_image(f))


def get_starwars_image_url(filename, starwars_side='Rebels'):
    """Returns the public MEDIA_URL for a Star Wars image basename.

    The basename is sanitized (path components stripped) so this cannot be
    coaxed into building a URL outside the Star Wars directory.
    """
    starwars_side = _normalize_starwars_side(starwars_side)
    filename = os.path.basename(filename)
    return settings.MEDIA_URL + '/'.join(
        (*STARWARS_SUBDIR, starwars_side, filename)
    )


def get_path_to_random_starwars_image(starwars_side='Rebels'):
    """Gets a random star wars image path to assign"""
    star_wars_path = get_starwars_image_dir(starwars_side)
    return os.path.join(star_wars_path, random.choice(list_starwars_images(starwars_side)))

def get_files_in_directory(dir_path):
    """Returns a list of files in the given directory"""
    return [os.path.join(dir_path, f) for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))]

def get_filename_no_ext(filename):
    """Returns the *just* filename without the extension (no other path information)"""
    return os.path.splitext(os.path.basename(filename))[0]

def get_filename_for_artifact(last_name, title, forum_name, date, ext, suffix=None, max_pub_title_length=-1):
    """Generates a filename from the provided content."""
    filename_without_ext = get_filename_without_ext_for_artifact(last_name, title, forum_name, date, suffix, max_pub_title_length)

    # Check if ext starts with a dot. If not, add it
    if not ext.startswith('.'):
        ext = '.' + ext

    # Combine filename with extension
    return filename_without_ext + ext

def get_filename_without_ext_for_artifact(last_name, title, forum_name, date, suffix=None, max_pub_title_length=-1):
    """Generates a filename from the provided content"""

    if not last_name:
        last_name = "None"

    last_name = last_name.replace(" ", "")
    year = date.year

    # Convert the string 'title' to title case (each word starts with an uppercase letter)
    # and only keeps alphanumeric characters
    title = ''.join(x for x in title.title() if x.isalnum())

    # Only get the first N characters of the string if max_pub_title_length set
    if max_pub_title_length > 0 and max_pub_title_length < len(title):
        title = title[0:max_pub_title_length]

    if forum_name:
        forum_name = forum_name.replace(" ", "")

    # Convert metadata into a filename
    new_filename_no_ext = f"{last_name}_{title}_"

    # Add the suffix
    if suffix is not None:
        new_filename_no_ext += suffix + '_'
    
    # Add the rest of the metadata
    new_filename_no_ext += f"{forum_name}{year}"

    return get_valid_filename(new_filename_no_ext)
    

def ensure_filename_is_unique(filename_with_full_path):
    """Will return a filename with full path that is guaranteed to be unique"""
    while os.path.exists(filename_with_full_path):
        _logger.debug(f"This filename with path exists {filename_with_full_path}, trying to generate a unique one")

        # Use a timestamp, which given how often we are uploading files, should be totally fine
        # and preferable to the long strings 
        full_path = os.path.dirname(filename_with_full_path)
        file_ext = os.path.splitext(os.path.basename(filename_with_full_path))[1]
        new_filename_without_ext = os.path.splitext(os.path.basename(filename_with_full_path))[0]
        filename_with_full_path = os.path.join(full_path, new_filename_without_ext + "-" + str(time.time()) + file_ext)  
    
    # Returns a guaranteed-to-be-unique filename (with full path)
    return filename_with_full_path

def rename_artifact_on_filesystem(file_field, new_filename):
    """Renames the artifact.name to the new filename. Careful: does not save it back to the database"""
    rename_artifact_in_db_and_filesystem(None, file_field, new_filename, update_db=False)

def rename_artifact_in_db_and_filesystem(model, file_field, new_filename, update_db=True):
    """Renames the artifact in the database and filesystem. 
       Guarantees that new_filename is unique by adding in a randomly generated unique id to the filename (if necessary)
       If the new_filename does not have an extension, it will be added automatically using existing metadata
    """

    if os.path.dirname(new_filename):
        raise ValueError(f"Filename {new_filename} should not contain a path.")

    old_filename_with_full_path = file_field.path
    old_filename_with_local_path = file_field.name
    old_local_path = os.path.dirname(file_field.name)
    old_full_path = os.path.dirname(old_filename_with_full_path)
    old_filename_ext = os.path.splitext(old_filename_with_full_path)[1]

    # Check if filename has an extension. If not, add one
    if not os.path.splitext(new_filename)[1]:
        # Add the extension to the new filename
        new_filename = new_filename + old_filename_ext

    # Use Django helper function to ensure a clean filename
    new_filename = get_valid_filename(new_filename)

    # Add in the media directory to ensure that the filename is unique
    new_filename_with_full_path = os.path.join(old_full_path, new_filename)
    new_filename_with_full_path = ensure_filename_is_unique(new_filename_with_full_path)

    # Actually rename the existing file (aka initial_path) but only if it exists (it should!)
    # We rename the file on the filesystem and in the database (these need to be in concordance!)
    if os.path.exists(old_filename_with_full_path):
        os.rename(old_filename_with_full_path, new_filename_with_full_path)
        _logger.debug(f"Renamed {old_filename_with_full_path} to {new_filename_with_full_path}")

        # Change the pdf_file path to point to the renamed file and save the artifact
        file_field.name = os.path.join(old_local_path, os.path.basename(new_filename_with_full_path))

        # Save it out to the database
        if update_db:
            _logger.debug(f"Calling model.save() on model={model} with artifact.name={file_field.name}")
            model.save()
        else:
            _logger.debug(
                f"Careful: update_db={update_db}, so we are not saving this new artifact.name={file_field.name} to the db."
                f"The old artifact.name={old_filename_with_local_path}. You should call model.save() to save these changes"
            )

        return new_filename_with_full_path
    else:
        _logger.error(f'The file {old_filename_with_full_path} does not exist and cannot be renamed to {new_filename_with_full_path}')
        _logger.error(f"Thus, we did not rename the file or call model.save()")
        return None
    
def generate_thumbnail_for_pdf(pdf_file_field, thumbnail_image_field, thumbnail_local_path):
    """
    Generates a JPEG thumbnail from the first page of a PDF file.

    Uses progressive DPI fallback (144 → 72 → 36) to handle memory-intensive
    PDFs like large posters or complex vector graphics.

    Args:
        pdf_file_field (models.FileField): The source PDF file.
        thumbnail_image_field (models.ImageField): Field to store the thumbnail reference.
        thumbnail_local_path (str): Relative path (from MEDIA_ROOT) for thumbnail storage.

    Returns:
        str | None: Full filesystem path to the generated thumbnail, or None if
            generation failed at all resolutions.

    Raises:
        ValueError: If the provided file is not a PDF.
    """
    # Validate file type (case-insensitive)
    if not pdf_file_field.name.lower().endswith('.pdf'):
        raise ValueError("The provided file is not a PDF.")

    _logger.debug(
        f"Generating thumbnail for PDF: {pdf_file_field.name}, "
        f"output path: {thumbnail_local_path}"
    )

    # Ensure thumbnail directory exists
    thumbnail_dir = os.path.join(settings.MEDIA_ROOT, thumbnail_local_path)
    os.makedirs(thumbnail_dir, exist_ok=True)

    # Build output filename
    pdf_filename_no_ext = os.path.splitext(os.path.basename(pdf_file_field.path))[0]
    thumbnail_filename = f"{pdf_filename_no_ext}.jpg"
    thumbnail_full_path = ensure_filename_is_unique(
        os.path.join(thumbnail_dir, thumbnail_filename)
    )

    # Progressive DPI fallback for memory-constrained environments
    # 144 = Retina/HiDPI, 72 = Standard, 36 = Large format fallback
    dpi_options = [144, 72, 36]

    for dpi in dpi_options:
        try:
            _logger.debug(f"Attempting thumbnail generation at {dpi} DPI...")
            with Image(filename=f"{pdf_file_field.path}[0]", resolution=dpi) as img:
                img.format = 'jpeg'
                img.background_color = Color('white')
                img.alpha_channel = 'remove'
                img.save(filename=thumbnail_full_path)

            _logger.debug(f"Thumbnail generated successfully at {dpi} DPI.")
            thumbnail_image_field.name = os.path.join(
                thumbnail_local_path, 
                os.path.basename(thumbnail_full_path)
            )
            return thumbnail_full_path

        except WandException as e:
            _logger.warning(f"Thumbnail generation failed at {dpi} DPI: {e}")
            continue

    _logger.error(f"Thumbnail generation failed at all resolutions for: {pdf_file_field.name}")
    return None


def get_pdf_page_count(pdf_file_field):
    """
    Returns the number of pages in the given PDF, or None if the count can't be
    determined (no file, not a PDF, file missing on disk, or unreadable/corrupt).

    Uses pypdf, which reads the PDF's internal page tree directly rather than
    rendering pages, so it stays fast and light even for large documents. This
    backs the auto-population of Publication.num_pages (issue #1298) so students
    no longer have to count pages by hand.

    Returning None rather than raising is intentional: a malformed PDF should
    never block saving a publication. The caller simply leaves num_pages unset.

    Args:
        pdf_file_field (models.FileField): The PDF file field to inspect.

    Returns:
        int | None: The page count, or None if it can't be determined.

    Example:
        >>> get_pdf_page_count(publication.pdf_file)
        12
    """
    if not pdf_file_field or not pdf_file_field.name:
        return None

    if not pdf_file_field.name.lower().endswith('.pdf'):
        _logger.debug(f"Not counting pages for non-PDF file: {pdf_file_field.name}")
        return None

    if not pdf_file_field.storage.exists(pdf_file_field.name):
        _logger.debug(f"Cannot count pages; file not found in storage: {pdf_file_field.name}")
        return None

    try:
        reader = PdfReader(pdf_file_field.path)
        return len(reader.pages)
    except (PdfReadError, OSError, ValueError) as e:
        _logger.warning(f"Could not determine page count for {pdf_file_field.name}: {e}")
        return None
