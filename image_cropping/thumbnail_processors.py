"""
easy_thumbnails processor that applies a stored crop box.

Registered ahead of the default easy_thumbnails processors in
``settings.THUMBNAIL_PROCESSORS`` so that any thumbnail rendered with
``box=obj.cropping`` is first cropped to the editor-chosen rectangle and then
resized. Ported verbatim from upstream django-image-cropping -- it is pure
Pillow and has no dependency on the (removed) backend/config layer.
"""

import logging

logger = logging.getLogger(__name__)


def crop_corners(image, box=None, **kwargs):
    """
    Crop ``image`` to the selection stored by an :class:`ImageRatioField`.

    ``box`` is either a string ``"x1,y1,x2,y2"`` or a four-item list/tuple of
    integers, in original-image pixel coordinates. Anything unparseable (or a
    negative first value, which signals "cropping disabled") leaves the image
    untouched.

    Example:
        >>> crop_corners(pil_image, box="10,10,210,210")  # 200x200 crop
    """
    if not box:
        return image

    if not isinstance(box, (list, tuple)):
        # convert cropping string to a list of integers if necessary
        try:
            box = list(map(int, box.split(",")))
        except (ValueError, AttributeError):
            # there's garbage in the cropping field, ignore
            logger.warning('Unable to parse "box" parameter "%s". Ignoring.', box)
            box = []

    if len(box) == 4:
        if box[0] < 0:
            # a negative first box value indicates that cropping is disabled
            return image
        width = abs(box[2] - box[0])
        height = abs(box[3] - box[1])
        if width and height and (width, height) != image.size:
            image = image.crop(box)
    else:
        logger.warning('"box" parameter requires four values. Ignoring "%r".', box)
    return image
