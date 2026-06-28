"""
Tests for the vendored ``image_cropping`` package (#1299 / #1269 sibling).

We replaced the abandoned PyPI ``django-image-cropping`` (v1.7, Feb 2022,
Jcrop + jQuery, Django <=4.0, "save first, then crop") with a small in-repo
fork whose only material change is a modern, client-side Cropper.js admin
widget that previews and crops *before* the first save. The data layer is
deliberately unchanged: ``ImageRatioField`` still stores an ``"x1,y1,x2,y2"``
box string and ``crop_corners`` still feeds that box to easy_thumbnails, so
every existing crop and every ``{% thumbnail ... box=obj.cropping %}`` call
site keeps working untouched.

These tests pin the three contracts that make that swap safe:

1. ``crop_corners`` box parsing (the public render path).
2. ``ImageRatioField.deconstruct()`` still returns the
   ``image_cropping.fields.ImageRatioField`` path -- this is the migration
   contract. ``website/migrations/`` is gitignored and regenerated per
   environment, and existing migration files ``import image_cropping.fields``;
   if this path drifts, ``migrate`` breaks on the next push-to-deploy with no
   way to fix it on the server (see CLAUDE.md server-access notes).
3. The admin widget is the Cropper.js one (no Jcrop/jQuery), and the field
   wires the model class up with the ``crop_fields`` / ``ratio_fields``
   metadata the mixin relies on.
"""

from unittest.mock import MagicMock

from django.test import SimpleTestCase


# --- crop_corners (public render path) -------------------------------------


class CropCornersTests(SimpleTestCase):
    """
    Unit tests for the thumbnail processor that turns a stored box string into
    an actual Pillow crop. This is what every ``box=obj.cropping`` template tag
    ultimately exercises, so its parsing rules are load-bearing.
    """

    def _image(self, size=(100, 100)):
        img = MagicMock()
        img.size = size
        # image.crop(box) returns a new image; hand back a sentinel so we can
        # assert the crop happened and with which box.
        img.crop.return_value = "cropped"
        return img

    def test_no_box_returns_image_unchanged(self):
        from image_cropping.thumbnail_processors import crop_corners

        img = self._image()
        for empty in (None, "", []):
            self.assertIs(crop_corners(img, box=empty), img)
        img.crop.assert_not_called()

    def test_valid_box_string_crops(self):
        from image_cropping.thumbnail_processors import crop_corners

        img = self._image(size=(100, 100))
        result = crop_corners(img, box="10,10,50,40")
        img.crop.assert_called_once_with([10, 10, 50, 40])
        self.assertEqual(result, "cropped")

    def test_box_as_tuple_crops(self):
        from image_cropping.thumbnail_processors import crop_corners

        img = self._image(size=(100, 100))
        crop_corners(img, box=(10, 10, 50, 40))
        img.crop.assert_called_once_with((10, 10, 50, 40))

    def test_negative_first_value_disables_cropping(self):
        from image_cropping.thumbnail_processors import crop_corners

        img = self._image()
        self.assertIs(crop_corners(img, box="-1,0,50,50"), img)
        img.crop.assert_not_called()

    def test_garbage_box_is_ignored(self):
        from image_cropping.thumbnail_processors import crop_corners

        img = self._image()
        self.assertIs(crop_corners(img, box="not,a,box"), img)
        img.crop.assert_not_called()

    def test_wrong_length_box_is_ignored(self):
        from image_cropping.thumbnail_processors import crop_corners

        img = self._image()
        self.assertIs(crop_corners(img, box="10,10,50"), img)
        img.crop.assert_not_called()

    def test_box_matching_full_size_is_noop(self):
        from image_cropping.thumbnail_processors import crop_corners

        img = self._image(size=(40, 40))
        # box describes the whole image -> nothing to crop
        self.assertIs(crop_corners(img, box="0,0,40,40"), img)
        img.crop.assert_not_called()


# --- ImageRatioField migration / model-wiring contract ---------------------


class ImageRatioFieldContractTests(SimpleTestCase):
    """
    Pins the migration-safety contract and the model-class metadata the admin
    mixin depends on. ``SimpleTestCase`` is fine: no DB rows are touched.
    """

    def test_deconstruct_path_is_stable(self):
        """The deconstruct path must stay ``image_cropping.fields.ImageRatioField``."""
        from image_cropping.fields import ImageRatioField

        field = ImageRatioField("image", "245x245", size_warning=True)
        field.set_attributes_from_name("cropping")
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "image_cropping.fields.ImageRatioField")
        self.assertEqual(args, ("image", "245x245"))
        # kwargs that existing migration files pass must round-trip.
        self.assertEqual(kwargs["size_warning"], True)
        self.assertIn("free_crop", kwargs)

    def test_field_is_charfield_storing_box_string(self):
        from django.db import models
        from image_cropping.fields import ImageRatioField

        field = ImageRatioField("image", "245x245")
        self.assertIsInstance(field, models.CharField)
        self.assertEqual(field.max_length, 255)

    def test_accepts_legacy_migration_kwargs(self):
        """Old migrations call the field with the full upstream kwarg set."""
        from image_cropping.fields import ImageRatioField

        # Must not raise.
        ImageRatioField(
            "image",
            "245x245",
            free_crop=False,
            adapt_rotation=False,
            allow_fullsize=False,
            verbose_name="cropping",
            help_text=None,
            hide_image_field=False,
            size_warning=True,
        )

    def test_formfield_exposes_cropper_data_attrs(self):
        from image_cropping.fields import ImageRatioField

        field = ImageRatioField("image", "245x245")
        field.set_attributes_from_name("cropping")
        attrs = field.formfield().widget.attrs
        self.assertEqual(attrs["data-image-field"], "image")
        self.assertEqual(attrs["data-ratio"], str(245 / 245.0))
        self.assertIn("image-ratio", attrs["class"])


# --- Person model picks up the field metadata ------------------------------


class PersonCropMetadataTests(SimpleTestCase):
    """The field's contribute_to_class must register crop/ratio metadata."""

    def test_person_exposes_crop_fields(self):
        from website.models import Person

        self.assertIn("image", Person.crop_fields)
        self.assertIn("easter_egg", Person.crop_fields)
        self.assertIn("cropping", Person.ratio_fields)
        self.assertIn("easter_egg_crop", Person.ratio_fields)

    def test_award_badge_exposes_crop_fields(self):
        """Award.badge gained a square crop so its public anchor stays uniform."""
        from website.models import Award

        self.assertIn("badge", Award.crop_fields)
        self.assertIn("badge_cropping", Award.ratio_fields)


# --- Admin uses the Cropper.js widget, not Jcrop ---------------------------


class CropWidgetTests(SimpleTestCase):
    """
    The whole point of the swap: the admin image field renders our Cropper.js
    widget, and its Media pulls Cropper assets rather than the EOL Jcrop/jQuery
    bundle.
    """

    def test_widget_media_uses_cropperjs_not_jcrop(self):
        from image_cropping.widgets import CropImageWidget

        media = str(CropImageWidget().media)
        self.assertIn("image_cropping/cropper.min.js", media)
        self.assertIn("image_cropping/cropper.min.css", media)
        self.assertIn("image_cropping/ml_cropper.js", media)
        # The EOL bits must be gone.
        self.assertNotIn("Jcrop", media)
        self.assertNotIn("image_cropping.min.js", media)

    def test_person_admin_image_field_uses_crop_widget(self):
        from django.contrib.auth.models import AnonymousUser
        from image_cropping.widgets import CropImageWidget
        from website.models import Person
        from website.admin.admin_site import ml_admin_site

        admin_obj = ml_admin_site._registry[Person]
        request = MagicMock()
        request.user = AnonymousUser()
        db_field = Person._meta.get_field("image")
        formfield = admin_obj.formfield_for_dbfield(db_field, request)
        self.assertIsInstance(formfield.widget, CropImageWidget)

    def test_award_admin_badge_field_uses_crop_widget(self):
        from django.contrib.auth.models import AnonymousUser
        from image_cropping.widgets import CropImageWidget
        from website.models import Award
        from website.admin.admin_site import ml_admin_site

        admin_obj = ml_admin_site._registry[Award]
        request = MagicMock()
        request.user = AnonymousUser()
        db_field = Award._meta.get_field("badge")
        formfield = admin_obj.formfield_for_dbfield(db_field, request)
        self.assertIsInstance(formfield.widget, CropImageWidget)
