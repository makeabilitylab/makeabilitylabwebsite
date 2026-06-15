"""
CropImageWidget - admin file input wired for client-side cropping.

Renders Django's standard admin file widget, but (a) advertises the current
image's URL via ``data-original-url`` so the JS can load it for re-cropping, and
(b) pulls in Cropper.js plus our glue code (``ml_cropper.js``) instead of the
retired Jcrop/jQuery bundle. All cropping happens in the browser; on submit
only the ``"x1,y1,x2,y2"`` box (in the sibling ratio field) is saved.
"""

import json

from django import forms
from django.contrib.admin.widgets import AdminFileWidget
from django.utils.safestring import mark_safe


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


class EasterEggCropImageWidget(CropImageWidget):
    """Crop widget for ``Person.easter_egg`` with a Star Wars figure picker.

    Extends :class:`CropImageWidget` so an editor can preview, crop, and
    *shuffle* a default Star Wars LEGO figure on a brand-new Person — before the
    first save — instead of waiting for ``Person.save()`` to assign one
    invisibly (issue #1304).

    It advertises the available figures to ``ml_cropper.js`` via two attrs on
    the file input:

    * ``data-starwars-images`` — a JSON array of ``{"name", "url"}`` objects.
    * ``data-starwars-choice-field`` — the name of the sibling hidden field
      (``easter_egg_starwars_choice``) into which the JS writes the chosen
      basename, so the server can copy that figure into the field on save.

    The list is supplied by the admin via ``widget.starwars_images`` (kept out
    of the widget so the widget stays free of model/filesystem imports).
    """

    #: Set by the admin before rendering: list of {"name", "url"} dicts.
    starwars_images = ()

    #: Name of the sibling hidden field the JS writes the chosen basename into.
    choice_field_name = "easter_egg_starwars_choice"

    def render(self, name, value, attrs=None, renderer=None):
        attrs = attrs or {}
        attrs["data-starwars-images"] = json.dumps(list(self.starwars_images))
        attrs["data-starwars-choice-field"] = self.choice_field_name
        html = super().render(name, value, attrs, renderer)
        # A real <button> (not a link) so keyboard/SR users get correct
        # semantics; type="button" keeps it from submitting the admin form.
        # ml_cropper.js finds it relative to the file input and wires it up.
        shuffle = (
            '<button type="button" class="ml-cropper__shuffle" '
            'data-starwars-shuffle hidden>'
            "\U0001f3b2 Shuffle Star Wars figure</button>"
        )
        return mark_safe(html + shuffle)
