"""
Pre-generate the cropped derivatives the public API serves (#1432).

The API's ``thumbnail`` fields are sizes the *site* never renders (256x256 for a
person, 1000x600 for a project), so without this the first API request after a
deploy generates them inline -- decoding up to a page's worth of multi-megabyte
source photos inside one request, which can approach the Gunicorn timeout set in
docker-entrypoint.sh. This command does that work once at container start.

It is idempotent and cheap on re-run: easy-thumbnails skips any derivative whose
file is already on disk and newer than its source, so subsequent starts are a
couple of stat calls per row. Safe to run by hand at any time::

    python manage.py warm_api_thumbnails
    python manage.py warm_api_thumbnails --dry-run   # just report what's covered

Scope matches what the API exposes: every person who has a photo -- not just lab
members, because PersonSummarySerializer also nests in publication ``authors``,
where external co-authors show up -- and every publicly visible project.
"""

import logging
import time

from django.core.management.base import BaseCommand

from website.api.serializers import (
    API_PERSON_THUMBNAIL_SIZE,
    API_PROJECT_THUMBNAIL_SIZE,
)
from website.models import Person, Project
from website.utils.thumbnail_utils import get_cropped_thumbnail

_logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Pre-generate the cropped thumbnails served by the public REST API (#1432)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report how many rows would be warmed without generating anything.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # Rows with no image at all are excluded here rather than skipped in the
        # loop: gallery_image is null=True, and Django's .exclude(field="")
        # keeps NULLs (NOT (x = '' AND x IS NOT NULL)), so both filters are
        # needed or image-less projects get reported as failures.
        people = Person.objects.exclude(image="").exclude(image__isnull=True)
        projects = (
            Project.objects.filter(is_visible=True)
            .exclude(gallery_image="")
            .exclude(gallery_image__isnull=True)
        )

        targets = [
            ("person", people, "image", "cropping", API_PERSON_THUMBNAIL_SIZE),
            ("project", projects, "gallery_image", "cropping",
             API_PROJECT_THUMBNAIL_SIZE),
        ]

        for label, queryset, image_attr, box_attr, size in targets:
            count = queryset.count()
            if dry_run:
                msg = f"[dry run] would warm {count} {label} thumbnail(s) at {size}"
                _logger.info(msg)
                self.stdout.write(msg)
                continue

            start = time.monotonic()
            generated = cached = failed = 0
            for obj in queryset.iterator():
                image, box = getattr(obj, image_attr), getattr(obj, box_attr)
                if get_cropped_thumbnail(image, size, box, generate=False):
                    cached += 1
                    continue
                if get_cropped_thumbnail(image, size, box) is None:
                    # get_cropped_thumbnail already logged the reason (usually a
                    # source file missing from media/); keep going.
                    failed += 1
                else:
                    generated += 1

            elapsed = time.monotonic() - start
            msg = (
                f"{label} thumbnails at {size}: {generated} generated, "
                f"{cached} already cached, {failed} failed (of {count}) "
                f"in {elapsed:.1f}s"
            )
            _logger.info(msg)
            self.stdout.write(msg)
