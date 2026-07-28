"""
Tests for the ``warm_api_thumbnails`` management command (#1432).

The command runs on every container start (docker-entrypoint.sh, step 4.10e) so
the first API request after a deploy doesn't have to generate every cropped
derivative inline. What matters is that it (a) actually produces the files the
API serves, (b) is safe to re-run, and (c) survives a row whose source image is
missing from media/ -- the startup sequence must never die on one bad row.
"""

import io
import os
import shutil
import tempfile
from datetime import date

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import override_settings
from PIL import Image

from website.api.serializers import (
    API_PERSON_THUMBNAIL_SIZE,
    API_PROJECT_THUMBNAIL_SIZE,
)
from website.models import Position
from website.models.position import Title
from website.tests.base import DatabaseTestCase
from website.utils.thumbnail_utils import get_cropped_thumbnail

_TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix="ml_warm_thumbs_")


def _png_upload(name, size=(800, 600)):
    buffer = io.BytesIO()
    Image.new("RGB", size, (10, 120, 200)).save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


@override_settings(MEDIA_ROOT=_TEST_MEDIA_ROOT)
class WarmApiThumbnailsTests(DatabaseTestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(_TEST_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def _member(self, first_name="Warm"):
        person = self.make_person(
            first_name=first_name,
            last_name="Member",
            image=_png_upload(f"{first_name.lower()}_member.png"),
            cropping="100,100,400,400",
        )
        Position.objects.create(
            person=person, start_date=date(2020, 1, 1), title=Title.PHD_STUDENT
        )
        return person

    def _cached_thumbnail_path(self, image_field, size, box):
        """Path of an ALREADY-cached derivative, or None.

        ``generate=False`` matters: asking the generating way would create the
        file, and every assertion here would pass whether or not the command
        actually did anything.
        """
        thumbnail = get_cropped_thumbnail(image_field, size, box, generate=False)
        if thumbnail is None:
            return None
        return os.path.join(settings.MEDIA_ROOT, thumbnail.name)

    def test_warms_member_and_visible_project_thumbnails(self):
        person = self._member()
        project = self.make_project(
            name="Warm Project",
            short_name="warmproject",
            is_visible=True,
            gallery_image=_png_upload("warm_project.png", size=(1600, 1200)),
            cropping="0,100,1500,1000",
        )
        self.assertIsNone(
            self._cached_thumbnail_path(
                person.image, API_PERSON_THUMBNAIL_SIZE, person.cropping
            ),
            "nothing should be cached before the command runs",
        )

        call_command("warm_api_thumbnails")

        person_thumb = self._cached_thumbnail_path(
            person.image, API_PERSON_THUMBNAIL_SIZE, person.cropping
        )
        project_thumb = self._cached_thumbnail_path(
            project.gallery_image, API_PROJECT_THUMBNAIL_SIZE, project.cropping
        )
        self.assertIsNotNone(person_thumb)
        self.assertIsNotNone(project_thumb)
        with Image.open(person_thumb) as img:
            self.assertEqual(img.size, API_PERSON_THUMBNAIL_SIZE)
        with Image.open(project_thumb) as img:
            self.assertEqual(img.size, API_PROJECT_THUMBNAIL_SIZE)

    def test_warms_people_who_are_not_lab_members(self):
        """External co-authors have no Position but are still served by the API,
        nested as publication ``authors``."""
        coauthor = self.make_person(
            first_name="External",
            last_name="Coauthor",
            image=_png_upload("external_coauthor.png"),
            cropping="0,0,400,400",
        )

        call_command("warm_api_thumbnails")

        self.assertIsNotNone(
            self._cached_thumbnail_path(
                coauthor.image, API_PERSON_THUMBNAIL_SIZE, coauthor.cropping
            )
        )

    def test_project_without_gallery_image_is_not_a_failure(self):
        """gallery_image is null=True, and .exclude(field="") keeps NULLs -- an
        image-less project must be filtered out, not reported as a failure."""
        self.make_project(name="No Image", short_name="noimage", is_visible=True)

        out = io.StringIO()
        call_command("warm_api_thumbnails", stdout=out)

        project_line = next(
            line for line in out.getvalue().splitlines() if line.startswith("project")
        )
        self.assertIn("0 failed (of 0)", project_line)

    def test_rerun_is_idempotent(self):
        """Second run must reuse the cached file, not rewrite it -- this runs on
        every container start."""
        person = self._member()
        call_command("warm_api_thumbnails")
        path = self._cached_thumbnail_path(
            person.image, API_PERSON_THUMBNAIL_SIZE, person.cropping
        )
        first_mtime = os.path.getmtime(path)

        out = io.StringIO()
        call_command("warm_api_thumbnails", stdout=out)

        self.assertEqual(os.path.getmtime(path), first_mtime)
        self.assertIn("0 generated", out.getvalue())

    def test_missing_source_file_does_not_abort_the_run(self):
        broken = self._member(first_name="Broken")
        default_storage.delete(broken.image.name)
        healthy = self._member(first_name="Healthy")

        with self.assertLogs("website.utils.thumbnail_utils", level="WARNING"):
            call_command("warm_api_thumbnails")

        self.assertIsNotNone(
            self._cached_thumbnail_path(
                healthy.image, API_PERSON_THUMBNAIL_SIZE, healthy.cropping
            )
        )

    def test_dry_run_generates_nothing(self):
        person = self._member()
        call_command("warm_api_thumbnails", "--dry-run")

        # Scoped to this person's own derivatives: MEDIA_ROOT is shared by every
        # test in this class, so a directory-wide check would depend on test order.
        self.assertIsNone(
            self._cached_thumbnail_path(
                person.image, API_PERSON_THUMBNAIL_SIZE, person.cropping
            )
        )
