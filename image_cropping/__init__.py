"""
image_cropping - in-repo fork of django-image-cropping (#1299 / #1269).

Why this package exists
-----------------------
We replaced the PyPI ``django-image-cropping`` (v1.7, Feb 2022; Jcrop +
jQuery; classifiers stop at Django 4.0; "save first, *then* crop") with this
small local fork. It is treated as project source code, exactly like
``sortedm2m_filter_horizontal_widget``.

What changed vs. upstream
-------------------------
- The admin widget is rewritten on **Cropper.js** (vendored, v1.6.2, MIT, no
  build step). It previews and crops the image *client-side, before the first
  save* -- closing the long-standing "upload, save, scroll up, crop" friction
  (#1299).
- The pluggable backend / ``django-appconf`` config layer is removed; we wire
  easy_thumbnails directly.

What deliberately did NOT change
--------------------------------
- ``ImageRatioField`` is still a ``CharField`` storing an ``"x1,y1,x2,y2"``
  box, and its ``deconstruct()`` still returns
  ``image_cropping.fields.ImageRatioField``. That keeps the DB column and every
  gitignored, per-environment migration that ``import image_cropping.fields``
  working -- critical because deploys are push-only with no server shell to
  repair a broken ``migrate`` (see CLAUDE.md).
- ``crop_corners`` still feeds the stored box to easy_thumbnails, so every
  ``{% thumbnail ... box=obj.cropping %}`` call site is untouched.

Keeping the package name ``image_cropping`` (rather than renaming) is
intentional: it is what preserves those migration imports.
"""

from .admin import ImageCroppingMixin
from .fields import ImageRatioField

__all__ = ["ImageCroppingMixin", "ImageRatioField"]
__version__ = "2.0.0-makelab"
