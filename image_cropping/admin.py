"""
Admin mixin that swaps the crop widget onto cropped ImageFields.

Add :class:`ImageCroppingMixin` to a ``ModelAdmin`` whose model has one or more
:class:`~image_cropping.fields.ImageRatioField`. For each ImageField referenced
by a ratio field, the file input is rendered with :class:`CropImageWidget`
(Cropper.js); the ratio field renders as a plain text input carrying the crop
box. ``ml_cropper.js`` wires the two together in the browser.
"""

from .widgets import CropImageWidget


class ImageCroppingMixin:
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        crop_fields = getattr(self.model, "crop_fields", {})
        if db_field.name in crop_fields:
            kwargs["widget"] = CropImageWidget
        return super().formfield_for_dbfield(db_field, request, **kwargs)
