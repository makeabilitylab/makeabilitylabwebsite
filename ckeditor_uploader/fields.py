"""
Compatibility shim for ``ckeditor_uploader.fields`` (issue #1269).

django-ckeditor (CKEditor 4) was removed in favor of django-prose-editor. Our
``website/migrations/`` are gitignored and per-environment, so older ones
(0001_initial, 0002, 0003) still ``import ckeditor_uploader.fields`` at load
time to reconstruct historical model state. With the real package gone, that
import would crash ``makemigrations``/``migrate`` on every container start — and
we cannot edit migrations on the servers (push-only deploys, no shell access).

This mirrors the in-repo ``image_cropping`` fork (see image_cropping/README.md
and CLAUDE.md): keep the import path alive with a minimal stand-in so historical
migrations load unchanged. ``News.content`` is now a
``django_prose_editor.fields.ProseEditorField``; a generated ``AlterField``
migration moves the column off this shim on first deploy. The DB column was
always a plain ``TEXT`` column, so the stand-in is just a ``TextField`` that
tolerates (and drops) CKEditor-only constructor kwargs and preserves the
original ``deconstruct()`` import path so the historical migrations round-trip.

Because the project root is first on ``sys.path``, this package shadows any
leftover site-packages copy; behavior is identical whether or not the real
django-ckeditor is still installed.
"""

from django.db import models

# CKEditor-only kwargs that historical field definitions might carry. They have
# no DB-schema meaning for a plain TextField, so we drop them on the way in.
_CKEDITOR_ONLY_KWARGS = (
    "config_name",
    "extra_plugins",
    "external_plugin_resources",
)


class RichTextUploadingField(models.TextField):
    """Minimal stand-in for the removed CKEditor uploading field.

    Behaves as a plain ``TextField`` but accepts and discards CKEditor-specific
    kwargs, and reports the original dotted path from ``deconstruct()`` so that
    gitignored historical migrations referencing
    ``ckeditor_uploader.fields.RichTextUploadingField`` keep loading.
    """

    def __init__(self, *args, **kwargs):
        for key in _CKEDITOR_ONLY_KWARGS:
            kwargs.pop(key, None)
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, _path, args, kwargs = super().deconstruct()
        return name, "ckeditor_uploader.fields.RichTextUploadingField", args, kwargs
