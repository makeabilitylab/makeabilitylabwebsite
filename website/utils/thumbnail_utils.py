"""
Server-side thumbnail generation that honors the editor's crop box.

Templates get cropped derivatives via ``{% thumbnail img size box=obj.cropping
crop detail upscale %}``, which silently renders an empty ``src`` if anything
goes wrong. Python callers (views, API serializers, management commands) have no
such safety net -- a missing source file raises
``easy_thumbnails.exceptions.InvalidImageFormatError``, and an unset ImageField
raises ``ValueError`` on ``.url``. :func:`get_cropped_thumbnail` is the one place
that handles both, so every non-template caller produces the *same* derivative
(same options, therefore the same filename on disk) as the site's templates.

Usage::

    from website.utils.thumbnail_utils import get_cropped_thumbnail

    thumb = get_cropped_thumbnail(person.image, (256, 256), person.cropping)
    url = thumb.url if thumb else person.image.url  # caller decides the fallback

**Match the requested size's aspect ratio to the model's ImageRatioField.**
``crop_corners`` applies the editor's box first, then easy-thumbnails'
``scale_and_crop`` resizes the result to ``size`` -- and center-crops a second
time if the aspect ratios disagree. That is what clipped heads off the news
cards in #1424.
"""

import logging

from easy_thumbnails.files import get_thumbnailer

_logger = logging.getLogger(__name__)


def get_cropped_thumbnail(image_field, size, box=None):
    """
    Generate (or fetch the cached) thumbnail of ``image_field`` at ``size``,
    applying the ``box`` crop set by an editor via django-image-cropping.

    Args:
        image_field: an ImageField/FieldFile (e.g. ``person.image``). May be
            empty/unset.
        size: ``(width, height)`` for the derivative. Keep the aspect ratio equal
            to the model's ImageRatioField -- see the module docstring.
        box: the crop box string stored by ``ImageRatioField``
            (``"x1,y1,x2,y2"``), or falsy for no crop.

    Returns:
        An ``easy_thumbnails`` ``ThumbnailFile`` (has ``.url``, ``.width``, ...),
        or ``None`` if there is no image or generation failed. Callers decide
        what to fall back to; failures are logged, never raised.
    """
    if not image_field:
        return None

    # Same option set the person/project templates pass, so the derivative
    # filename (and thus the cached file) is shared with the rendered site.
    options = {
        "size": size,
        "crop": True,
        "upscale": True,
        "detail": True,
    }
    if box:
        options["box"] = box

    try:
        return get_thumbnailer(image_field).get_thumbnail(options)
    except Exception:
        _logger.warning(
            "Thumbnail generation failed for %s at %s.",
            getattr(image_field, "name", image_field),
            size,
            exc_info=True,
        )
        return None
