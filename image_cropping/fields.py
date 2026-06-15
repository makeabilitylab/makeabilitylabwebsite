"""
ImageRatioField - stores a crop box for an associated ImageField.

A thin ``CharField`` that holds an ``"x1,y1,x2,y2"`` rectangle (original-image
pixel coordinates). It does not store an image itself; it records *how* a
sibling ``ImageField`` should be cropped, and easy_thumbnails renders the crop
on demand via :func:`image_cropping.thumbnail_processors.crop_corners`.

Ported from upstream django-image-cropping with the appconf/backend layer
removed. The constructor signature, ``deconstruct()`` output, and the
``crop_fields`` / ``ratio_fields`` model metadata are kept identical to
upstream so existing (gitignored, per-environment) migrations and the admin
mixin keep working unchanged. See the package docstring for the full rationale.
"""

from django import forms
from django.db import models
from django.db.models import signals


def max_cropping(width, height, image_width, image_height, free_crop=False):
    """
    Return the largest centered box of aspect ratio ``width/height`` that fits
    inside an ``image_width`` x ``image_height`` image, as ``[x1, y1, x2, y2]``.

    Used to seed a sensible default crop when none has been set yet.
    """
    if free_crop:
        return [0, 0, image_width, image_height]

    ratio = width / float(height)
    if image_width < image_height * ratio:
        # width fits fully, height needs to be cropped
        offset = int(round((image_height - (image_width / ratio)) / 2))
        return [0, offset, image_width, image_height - offset]

    # height fits fully, width needs to be cropped
    offset = int(round((image_width - (image_height * ratio)) / 2))
    return [offset, 0, image_width - offset, image_height]


def _image_size(image):
    """Return (width, height) for an image file, honoring EXIF orientation."""
    try:
        return image.width, image.height
    except AttributeError:
        # Fall back to opening the file (e.g. freshly uploaded, not yet saved).
        from easy_thumbnails.source_generators import pil_image
        return pil_image(image).size


class ImageRatioField(models.CharField):
    """
    Store the crop boundaries for ``image_field`` at a fixed aspect ratio.

    Args:
        image_field: name of the sibling ``ImageField`` to crop. (Upstream also
            supported ``"fk_field__image"`` for cropping an image on a related
            object; that path is unused here but the kwarg is still accepted.)
        size: ``"WIDTHxHEIGHT"`` -- defines both the aspect ratio and the
            minimum acceptable crop size.
        free_crop: if True, allow any aspect ratio.
        size_warning: if True, warn in the admin when the chosen crop is
            smaller than ``size``.

    ``adapt_rotation``, ``allow_fullsize``, and ``hide_image_field`` are
    accepted for migration/back-compat but are not otherwise used.
    """

    def __init__(
        self,
        image_field,
        size="0x0",
        free_crop=False,
        adapt_rotation=False,
        allow_fullsize=False,
        verbose_name=None,
        help_text=None,
        hide_image_field=False,
        size_warning=False,
    ):
        if "__" in image_field:
            self.image_field, self.image_fk_field = image_field.split("__")
        else:
            self.image_field, self.image_fk_field = image_field, None
        self.width, self.height = list(map(int, size.split("x")))
        self.free_crop = free_crop
        self.adapt_rotation = adapt_rotation
        self.allow_fullsize = allow_fullsize
        self.size_warning = size_warning
        self.hide_image_field = hide_image_field
        super().__init__(
            max_length=255,
            default="",
            blank=True,
            verbose_name=verbose_name,
            help_text=help_text,
        )

    def deconstruct(self):
        """
        Return migration-serialization data.

        IMPORTANT: the returned path is hard-pinned to
        ``"image_cropping.fields.ImageRatioField"``. Existing migration files
        (gitignored, regenerated per environment) reference exactly this path;
        changing it would break ``migrate`` on the next push-to-deploy with no
        way to fix it server-side. Pinned by a regression test.
        """
        if self.image_fk_field:
            image_field = "%s__%s" % (self.image_field, self.image_fk_field)
        else:
            image_field = self.image_field

        args = (image_field, "%dx%d" % (self.width, self.height))
        kwargs = {
            "free_crop": self.free_crop,
            "adapt_rotation": self.adapt_rotation,
            "allow_fullsize": self.allow_fullsize,
            "verbose_name": self.verbose_name,
            "help_text": self.help_text,
            "hide_image_field": self.hide_image_field,
            "size_warning": self.size_warning,
        }
        return self.name, "image_cropping.fields.ImageRatioField", args, kwargs

    def contribute_to_class(self, cls, name, **kwargs):
        super().contribute_to_class(cls, name, **kwargs)
        if not cls._meta.abstract:
            # Record which ImageFields are cropped (so the admin mixin can swap
            # in the crop widget) and which ratio fields exist on the model.
            if not hasattr(cls, "crop_fields"):
                cls.add_to_class("crop_fields", {})
            cls.crop_fields[self.image_field] = {
                "fk_field": self.image_fk_field,
                "hidden": self.hide_image_field,
            }

            if not hasattr(cls, "ratio_fields"):
                cls.add_to_class("ratio_fields", [])
            cls.ratio_fields.append(name)

            signals.pre_save.connect(self.initial_cropping, sender=cls)

    def initial_cropping(self, sender, instance, *args, **kwargs):
        """
        Seed an empty ratio field with a centered max-area box on save, so a
        sensible crop exists even if the editor never touched the widget (or
        had JavaScript disabled).
        """
        for ratiofieldname in getattr(instance, "ratio_fields", []):
            if getattr(instance, ratiofieldname):
                continue  # cropping already set

            ratiofield = instance._meta.get_field(ratiofieldname)
            image = getattr(instance, ratiofield.image_field)
            if ratiofield.image_fk_field and image:  # image is on a ForeignKey
                image = getattr(image, ratiofield.image_fk_field)
            if not image:
                continue

            try:
                width, height = _image_size(image)
                box = max_cropping(
                    ratiofield.width,
                    ratiofield.height,
                    width,
                    height,
                    free_crop=ratiofield.free_crop,
                )
                box = ",".join(map(str, box))
            except (IOError, OSError):
                box = ""
            setattr(instance, ratiofieldname, box)

    def formfield(self, **kwargs):
        """
        Render as a text input carrying the data-* attributes that
        ``ml_cropper.js`` reads to drive Cropper.js. The input itself holds the
        ``"x1,y1,x2,y2"`` value the JS writes back.
        """
        ratio = 0 if self.free_crop else self.width / float(self.height)
        kwargs["widget"] = forms.TextInput(
            attrs={
                "class": "image-ratio",
                "data-image-field": self.image_field,
                "data-my-name": self.name,
                "data-ratio": str(ratio),
                "data-min-width": self.width,
                "data-min-height": self.height,
                "data-size-warning": str(self.size_warning).lower(),
            }
        )
        return super().formfield(**kwargs)
