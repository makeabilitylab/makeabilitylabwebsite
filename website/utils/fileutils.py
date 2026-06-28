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


def pad_image_to_square(image_file):
    """Pad a non-square image to a centered square, returning a Django
    ``ContentFile`` of the padded image and the matching full-image crop box.

    Returns ``(ContentFile, "0,0,side,side")`` when padding was applied, or
    ``None`` when the image is already square or can't be read (so the caller
    leaves the original upload untouched).

    Why this exists (#1410)
    -----------------------
    Several admin image fields (Award.badge today; Person/Sponsor are similar)
    are cropped to a fixed 1:1 square via ``image_cropping`` + Cropper.js. For a
    logo or emblem that isn't square, cropping to a square *chops off content*.
    Editors usually want the opposite: keep the whole image and add blank
    margins -- exactly what they'd otherwise do by hand in an external editor
    before uploading. This does that padding for them, keeping the original
    pixels centered (equal margins on the two short sides).

    Why server-side (and not in the browser)
    ----------------------------------------
    The cropper's instant preview is client-side, so the obvious worry is that
    padding on the server would make the preview lie. We deliberately keep the
    *transform* here anyway: it's a ~15-line Pillow operation (Pillow is already
    a dependency) versus a much fiddlier client-side canvas + file-replacement
    dance, and it works regardless of the browser. The admin keeps an honest
    preview cheaply with CSS ``object-fit: contain`` (see pad_to_square.js):
    when "pad to square" is checked the interactive cropper is hidden -- there
    is nothing to crop -- and a letterboxed preview shows what will be saved.
    The caller then stores a full-image crop box so the existing
    ``crop_corners`` render path is a no-op on the already-square file.

    Background fill follows the format: PNG/WebP (alpha-capable) get
    *transparent* margins so the badge blends onto any page background; JPEG
    (no alpha) gets *white* margins. GIF/other are normalized to transparent
    PNG. Output format/extension otherwise match the upload so the upload
    validator and on-disk naming are unaffected.

    A note on lossy formats: padding always requires re-encoding -- you can't
    "insert" margin pixels into a compressed JPEG/WebP stream (it's stored as
    DCT/compressed blocks, not addressable pixels), so Pillow decodes the whole
    image to a bitmap, we paste it centered, and the *entire* image is encoded
    again. We don't reuse the source's original compression scheme: JPEG is
    re-encoded at a fixed quality=92 (Pillow's quality="keep" only works on an
    unmodified image, and pasting onto a larger canvas modifies it), which costs
    one extra, visually negligible generation of compression on the flat
    logos/emblems badges usually are. WebP is saved lossless so a lossless
    source isn't silently degraded; PNG/GIF are lossless anyway. Already-square
    uploads return ``None`` and are never re-encoded at all.
    """
    from io import BytesIO
    from PIL import Image, ImageOps
    from django.core.files.base import ContentFile

    name = getattr(image_file, "name", "") or "image"
    try:
        image_file.seek(0)
        img = Image.open(image_file)
        fmt = (img.format or "").upper()  # captured before transpose drops it
        # Respect EXIF orientation so a phone photo isn't padded sideways; this
        # also matches how the browser renders the <img> in the CSS preview.
        img = ImageOps.exif_transpose(img)
    except Exception:
        # Unreadable/corrupt image: let the normal upload path (and the upload
        # validator) handle it rather than crashing the save.
        _logger.warning("pad_image_to_square: could not read %s; skipping", name)
        return None

    width, height = img.size
    if width == height:
        return None  # already square -> keep the original bytes untouched

    side = max(width, height)
    offset = ((side - width) // 2, (side - height) // 2)
    orig_ext = os.path.splitext(name)[1].lstrip(".").lower()

    if fmt in ("JPEG", "JPG"):
        # No alpha channel: center the image on a white square.
        base = img.convert("RGB")
        canvas = Image.new("RGB", (side, side), (255, 255, 255))
        canvas.paste(base, offset)
        save_fmt = "JPEG"
        ext = orig_ext if orig_ext in ("jpg", "jpeg") else "jpg"
    elif fmt in ("PNG", "WEBP"):
        # Alpha-capable: transparent margins so the badge blends on any bg.
        base = img.convert("RGBA")
        canvas = Image.new("RGBA", (side, side), (255, 255, 255, 0))
        canvas.paste(base, offset, base)  # use alpha as its own paste mask
        save_fmt = fmt
        ext = orig_ext if orig_ext in ("png", "webp") else fmt.lower()
    else:
        # GIF or anything else: normalize to a transparent PNG.
        base = img.convert("RGBA")
        canvas = Image.new("RGBA", (side, side), (255, 255, 255, 0))
        canvas.paste(base, offset, base)
        save_fmt = "PNG"
        ext = "png"

    buffer = BytesIO()
    save_kwargs = {"format": save_fmt}
    if save_fmt == "JPEG":
        # Lossy + block-based: padding re-encodes the whole image (see docstring).
        # Fixed quality=92 -- the source's own quantization tables can't be
        # reused once we paste onto a larger canvas.
        save_kwargs["quality"] = 92
    elif save_fmt == "WEBP":
        # WebP defaults to lossy (quality 80); force lossless so a lossless
        # source isn't silently degraded by the re-encode that padding requires.
        save_kwargs["lossless"] = True
    canvas.save(buffer, **save_kwargs)

    base_name = os.path.splitext(os.path.basename(name))[0] or "badge"
    content = ContentFile(buffer.getvalue(), name="{}.{}".format(base_name, ext))
    return content, "0,0,{0},{0}".format(side)

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

    # Ensure the new filename carries the original file's extension. We compare
    # against the actual extension (endswith) rather than os.path.splitext():
    # callers pass standardized names that legitimately contain dots (e.g.
    # "...SciencesD.C.ArtScience...2014", "...Dr.SangMook2009"), and splitext
    # would treat the text after the last dot as an "extension" and skip adding
    # the real .pdf/.pptx — renaming the file extension-less on disk (#1390).
    if old_filename_ext and not new_filename.lower().endswith(old_filename_ext.lower()):
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
