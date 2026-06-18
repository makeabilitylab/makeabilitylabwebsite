"""
Tests for Person.save() side effects (#1278, item 5).

Person.save() does three non-obvious things on top of a normal save:
1. derives a unique url_name (already covered in test_recompute_url_names),
2. stamps bio_datetime_modified when the bio is first set or changes,
3. fills empty image / easter_egg fields with a random Star Wars figure.

(2) and (3) had no coverage. The Star Wars branch reads a real file off
media/, so these tests redirect MEDIA_ROOT to a temp dir and patch the picker
to return a controlled stand-in -- exercising the branch logic without touching
real media or depending on the figure set's contents.
"""

import os
import shutil
import tempfile
from unittest.mock import patch

from django.test import override_settings
from django.utils import timezone

from website.models import Person
from website.tests.base import DatabaseTestCase
from website.tests.factories import _GIF_1PX, image_upload

_PICKER = "website.models.person.ml_fileutils.get_path_to_random_starwars_image"


class PersonStarWarsFallbackTests(DatabaseTestCase):
    """Empty image fields are backfilled with a random Star Wars figure."""

    def setUp(self):
        super().setUp()
        # Temp media so the auto-assigned image is copied somewhere disposable,
        # never into the real media/ tree.
        self.media_root = tempfile.mkdtemp(prefix="ml_person_test_")
        self.addCleanup(shutil.rmtree, self.media_root, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=self.media_root)
        override.enable()
        self.addCleanup(override.disable)

        # A stand-in figure the patched picker hands back.
        self.fake_figure = os.path.join(self.media_root, "fake_rebel.gif")
        with open(self.fake_figure, "wb") as fh:
            fh.write(_GIF_1PX)

    @patch(_PICKER)
    def test_missing_image_and_easter_egg_are_auto_assigned(self, mock_pick):
        mock_pick.return_value = self.fake_figure

        person = Person(first_name="No", last_name="Image")
        person.save()

        self.assertTrue(person.image, "image should be auto-assigned when unset")
        self.assertTrue(
            person.easter_egg, "easter_egg should be auto-assigned when unset"
        )
        # Both fields were empty, so the picker is consulted once per field.
        self.assertEqual(mock_pick.call_count, 2)

    @patch(_PICKER)
    def test_provided_images_are_left_untouched(self, mock_pick):
        mock_pick.return_value = self.fake_figure

        person = Person(
            first_name="Has",
            last_name="Image",
            image=image_upload("custom_head.gif"),
            easter_egg=image_upload("custom_egg.gif"),
        )
        person.save()

        # Both fields were provided, so the Star Wars fallback must not fire.
        # (Person's upload_to renames the file from the person's name, so we
        # assert on the fallback not running rather than the stored filename.)
        mock_pick.assert_not_called()
        self.assertTrue(person.image)
        self.assertTrue(person.easter_egg)


class PersonBioDatetimeModifiedTests(DatabaseTestCase):
    """bio_datetime_modified tracks when the bio text was last changed."""

    def test_set_on_create(self):
        person = self.make_person()
        self.assertEqual(person.bio_datetime_modified, timezone.now().date())

    def test_updated_when_bio_changes(self):
        person = self.make_person(bio="original bio")
        # Backdate it so a real update is observable.
        Person.objects.filter(pk=person.pk).update(
            bio_datetime_modified="2000-01-01"
        )
        person.refresh_from_db()

        person.bio = "a brand new bio"
        person.save()

        self.assertEqual(person.bio_datetime_modified, timezone.now().date())

    def test_not_bumped_when_bio_unchanged(self):
        person = self.make_person(bio="stable bio")
        Person.objects.filter(pk=person.pk).update(
            bio_datetime_modified="2000-01-01"
        )
        person.refresh_from_db()

        # An unrelated edit must not touch the bio timestamp.
        person.last_name = "Renamed"
        person.save()

        person.refresh_from_db()
        self.assertEqual(str(person.bio_datetime_modified), "2000-01-01")
