"""
CropImageWidget - admin file input wired for client-side cropping.

Renders Django's standard admin file widget, but (a) advertises the current
image's URL via ``data-original-url`` so the JS can load it for re-cropping, and
(b) pulls in Cropper.js plus our glue code (``ml_cropper.js``) instead of the
retired Jcrop/jQuery bundle. All cropping happens in the browser; on submit
only the ``"x1,y1,x2,y2"`` box (in the sibling ratio field) is saved.
"""

from django import forms
from django.contrib.admin.widgets import AdminFileWidget


class CropImageWidget(AdminFileWidget):
    class Media:
        css = {
            "all": (
                "image_cropping/cropper.min.css",
                "image_cropping/ml_cropper.css",
            )
        }
        js = (
            "image_cropping/cropper.min.js",
            "image_cropping/ml_cropper.js",
        )

    def render(self, name, value, attrs=None, renderer=None):
        attrs = attrs or {}
        attrs["class"] = (attrs.get("class", "") + " crop-image-field").strip()
        # Expose the existing image so the JS can initialize Cropper against the
        # full-resolution original (keeps crop coordinates in natural pixels).
        if value and hasattr(value, "url"):
            try:
                attrs["data-original-url"] = value.url
            except ValueError:
                # No file associated (e.g. cleared) -> nothing to preview.
                pass
        return super().render(name, value, attrs, renderer)
