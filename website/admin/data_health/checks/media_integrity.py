"""
Data-health check: artifact file references vs. files on disk.

Surfaces two problems for Publication / Talk / Poster:
  * **missing-file** — a ``pdf_file`` / ``raw_file`` / ``thumbnail`` field is
    set but the file no longer exists on disk.
  * **orphan-file** — a file sits under an upload/thumbnail dir with no DB
    row pointing at it (what ``delete_unused_files`` would remove).

The orphan-file scan mirrors the glob+filter logic in
``website/management/commands/delete_unused_files.py`` (excluding the
easy-thumbnails ``_detail`` variants). Read-only — it never deletes.
"""

import glob
import os

from django.conf import settings
from django.urls import reverse

from website.admin.data_health.registry import HealthCheck, register_check
from website.models import Poster, Publication, Talk

# (model, file-field name, extensions to scan for orphans in UPLOAD_DIR)
_FILE_FIELDS = [
    ('pdf_file', ['*.pdf']),
    ('raw_file', ['*.pptx', '*.key', '*.ai', '*.fig']),
]


def _safe_path(file_field):
    """Return a FileField's filesystem path, or None if unavailable."""
    try:
        return file_field.path
    except (ValueError, NotImplementedError):
        return None


@register_check
class MediaIntegrityCheck(HealthCheck):
    slug = 'media-integrity'
    title = 'Media / file integrity'
    description = (
        'Artifact file fields pointing at missing files, plus orphaned files '
        'on disk with no DB reference (what delete_unused_files would remove).'
    )
    group = 'Artifacts'
    columns = ['type', 'id', 'title', 'field', 'path', 'status']

    def get_rows(self):
        rows = []
        for model in (Publication, Talk, Poster):
            rows.extend(self._missing_files(model))
            rows.extend(self._orphan_files(model))
        return rows

    def row_link(self, row):
        """Deep-link a ``missing-file`` row to its artifact's admin edit page so
        the editor can re-upload the file or clear the dead reference right
        there (mirrors the action buttons on the other checks).

        ``orphan-file`` rows have no DB object to open — they're files on disk
        that ``delete_unused_files`` would remove — so they get no link.
        """
        if row.get('status') != 'missing-file' or not row.get('id'):
            return None
        url = reverse(f"admin:website_{row['type'].lower()}_change",
                      args=[row['id']])
        return ('Open →', url)

    def _missing_files(self, model):
        """DB rows whose file field is set but the file is gone from disk."""
        rows = []
        for obj in model.objects.all():
            for field_name in ('pdf_file', 'raw_file', 'thumbnail'):
                field = getattr(obj, field_name, None)
                if not field:
                    continue
                path = _safe_path(field)
                if path and not os.path.exists(path):
                    rows.append({
                        'type': model.__name__,
                        'id': obj.pk,
                        'title': obj.title or '',
                        'field': field_name,
                        'path': field.name,
                        'status': 'missing-file',
                    })
        return rows

    def _orphan_files(self, model):
        """Files on disk under the model's dirs with no DB reference."""
        rows = []

        # Build the set of basenames the DB references for this model.
        referenced = set()
        for obj in model.objects.all():
            for field_name in ('pdf_file', 'raw_file', 'thumbnail'):
                field = getattr(obj, field_name, None)
                if field and field.name:
                    referenced.add(os.path.basename(field.name))

        # Scan UPLOAD_DIR for pdf/raw files and THUMBNAIL_DIR for jpgs.
        scan = []
        upload_dir = os.path.join(settings.MEDIA_ROOT, model.UPLOAD_DIR)
        for patterns in (exts for _, exts in _FILE_FIELDS):
            for pattern in patterns:
                scan.extend(glob.glob(os.path.join(upload_dir, pattern)))
        thumb_dir = os.path.join(settings.MEDIA_ROOT, model.THUMBNAIL_DIR)
        scan.extend(glob.glob(os.path.join(thumb_dir, '*.jpg')))

        for full_path in scan:
            basename = os.path.basename(full_path)
            if '_detail' in basename:
                continue  # easy-thumbnails variant; handled by its own cleanup
            if basename in referenced:
                continue
            rows.append({
                'type': model.__name__,
                'id': '',
                'title': '',
                'field': '',
                'path': full_path,
                'status': 'orphan-file',
            })
        return rows
