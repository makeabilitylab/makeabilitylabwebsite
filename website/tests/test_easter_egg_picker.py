"""
Tests for the Star Wars easter-egg picker in the Person admin (#1304).

A brand-new Person has no ``easter_egg`` image, so historically the Cropper.js
widget had nothing to show until ``Person.save()`` assigned a *random* figure
server-side — invisible and un-croppable until after the first save. The picker
lets an editor preview / crop / shuffle a default figure up front; the chosen
figure's basename rides along in a hidden ``easter_egg_starwars_choice`` field
that ``PersonAdminForm`` copies into the model on save.

These tests pin that default-vs-chosen logic and its security gate:

1. The figure list (``fileutils.list_starwars_images``) is the single source of
   truth and the random picker draws from it.
2. A valid choice is copied into ``easter_egg`` when nothing was uploaded.
3. An uploaded image always wins over a choice.
4. With neither, ``Person.save()``'s random fallback still fires (preserving the
   original, non-admin/bulk behavior).
5. A crafted choice (path traversal / unknown name) is rejected.
"""

import os

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase

import website.utils.fileutils as ml_fileutils
from website.tests.factories import _GIF_1PX


# --- figure listing (single source of truth) -------------------------------


class StarWarsImageListingTests(SimpleTestCase):
    """The figure list backs both the random default and the admin picker."""

    def test_list_is_nonempty_and_all_images(self):
        images = ml_fileutils.list_starwars_images()
        self.assertTrue(images, "expected Star Wars figures under media/")
        self.assertTrue(all(ml_fileutils.is_image(name) for name in images))

    def test_random_default_is_drawn_from_the_list(self):
        path = ml_fileutils.get_path_to_random_starwars_image()
        self.assertIn(
            os.path.basename(path), ml_fileutils.list_starwars_images()
        )

    def test_image_url_points_into_the_figure_directory(self):
        name = ml_fileutils.list_starwars_images()[0]
        url = ml_fileutils.get_starwars_image_url(name)
        self.assertTrue(url.startswith(settings.MEDIA_URL))
        self.assertIn("StarWarsFiguresFullSquare/Rebels/", url)
        self.assertTrue(url.endswith(name))

    def test_image_url_strips_path_components(self):
        # Even if handed a traversal-ish value, the URL stays in the directory.
        url = ml_fileutils.get_starwars_image_url("../../secret.png")
        self.assertTrue(url.endswith("/secret.png"))
        self.assertNotIn("..", url)


# --- PersonAdminForm default-vs-chosen logic -------------------------------


class EasterEggChoiceFormTests(TestCase):
    """Exercises ``PersonAdminForm.save`` across the three easter-egg paths."""

    def setUp(self):
        # Person.save() writes the headshot + easter egg into media/person/;
        # track and remove them so tests don't litter the bind-mounted media.
        self._created_files = []

    def tearDown(self):
        for path in self._created_files:
            try:
                os.remove(path)
            except OSError:
                pass

    def _track(self, person):
        for filefield in (person.image, person.easter_egg):
            if filefield:
                try:
                    self._created_files.append(filefield.path)
                except (ValueError, NotImplementedError):
                    pass
        return person

    def _data(self, **extra):
        data = {"first_name": "Egg", "last_name": "Picker"}
        data.update(extra)
        return data

    def test_chosen_figure_is_copied_when_no_upload(self):
        from website.admin.person_admin import PersonAdminForm

        choice = ml_fileutils.list_starwars_images()[0]
        form = PersonAdminForm(data=self._data(easter_egg_starwars_choice=choice))
        self.assertTrue(form.is_valid(), form.errors)
        person = self._track(form.save())

        self.assertTrue(person.easter_egg)
        # The saved easter egg is a byte-for-byte copy of the chosen figure...
        src = os.path.join(ml_fileutils.get_starwars_image_dir(), choice)
        with open(src, "rb") as original:
            person.easter_egg.open("rb")
            try:
                self.assertEqual(person.easter_egg.read(), original.read())
            finally:
                person.easter_egg.close()
        # ...and a crop box was seeded (by ImageRatioField.initial_cropping).
        self.assertTrue(person.easter_egg_crop)

    def test_existing_easter_egg_can_be_swapped_to_a_figure(self):
        """An editor can shuffle a figure onto a Person that already has one."""
        from website.admin.person_admin import PersonAdminForm
        from website.models import Person

        person = self._track(
            Person.objects.create(
                first_name="Egg",
                last_name="Picker",
                image=SimpleUploadedFile("h.gif", _GIF_1PX, content_type="image/gif"),
                easter_egg=SimpleUploadedFile(
                    "old.gif", _GIF_1PX, content_type="image/gif"
                ),
            )
        )

        choice = ml_fileutils.list_starwars_images()[0]
        form = PersonAdminForm(
            data=self._data(easter_egg_starwars_choice=choice), instance=person
        )
        self.assertTrue(form.is_valid(), form.errors)
        updated = self._track(form.save())

        src = os.path.join(ml_fileutils.get_starwars_image_dir(), choice)
        with open(src, "rb") as original:
            updated.easter_egg.open("rb")
            try:
                self.assertEqual(updated.easter_egg.read(), original.read())
            finally:
                updated.easter_egg.close()

    def test_existing_easter_egg_kept_when_picker_untouched(self):
        """Editing a Person without shuffling leaves the easter egg unchanged."""
        from website.admin.person_admin import PersonAdminForm
        from website.models import Person

        person = self._track(
            Person.objects.create(
                first_name="Egg",
                last_name="Picker",
                image=SimpleUploadedFile("h.gif", _GIF_1PX, content_type="image/gif"),
                easter_egg=SimpleUploadedFile(
                    "old.gif", _GIF_1PX, content_type="image/gif"
                ),
            )
        )
        original_name = person.easter_egg.name

        form = PersonAdminForm(data=self._data(bio="updated"), instance=person)
        self.assertTrue(form.is_valid(), form.errors)
        updated = form.save()
        self.assertEqual(updated.easter_egg.name, original_name)

    def test_upload_wins_over_choice(self):
        from website.admin.person_admin import PersonAdminForm

        choice = ml_fileutils.list_starwars_images()[0]
        upload = SimpleUploadedFile("mine.gif", _GIF_1PX, content_type="image/gif")
        form = PersonAdminForm(
            data=self._data(easter_egg_starwars_choice=choice),
            files={"easter_egg": upload},
        )
        self.assertTrue(form.is_valid(), form.errors)
        person = self._track(form.save())

        # The saved file is the uploaded GIF, not the (larger) Star Wars figure.
        person.easter_egg.open("rb")
        try:
            self.assertEqual(person.easter_egg.read(), _GIF_1PX)
        finally:
            person.easter_egg.close()

    def test_random_fallback_when_untouched(self):
        """No upload + no choice -> Person.save() still assigns a figure."""
        from website.admin.person_admin import PersonAdminForm

        form = PersonAdminForm(data=self._data())
        self.assertTrue(form.is_valid(), form.errors)
        person = self._track(form.save())
        self.assertTrue(person.easter_egg)

    def test_unknown_choice_is_rejected(self):
        from website.admin.person_admin import PersonAdminForm

        for bad in ("../../../etc/passwd", "not-a-real-figure.png", "/etc/hosts"):
            form = PersonAdminForm(
                data=self._data(easter_egg_starwars_choice=bad)
            )
            self.assertFalse(form.is_valid(), f"{bad!r} should be rejected")
            self.assertIn("easter_egg_starwars_choice", form.errors)
