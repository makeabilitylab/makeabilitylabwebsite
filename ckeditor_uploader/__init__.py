"""
In-repo compatibility shim for the removed ``ckeditor_uploader`` package (#1269).

django-ckeditor (CKEditor 4) was replaced by django-prose-editor. This package
is NOT a Django app and is not in INSTALLED_APPS; it exists only so historical,
gitignored migration files can still ``import ckeditor_uploader.fields``. See
``ckeditor_uploader/fields.py`` for the full rationale.
"""
