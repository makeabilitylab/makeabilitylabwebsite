# image_cropping (in-repo fork)

A small local fork of [django-image-cropping](https://github.com/jonasundderwolf/django-image-cropping),
treated as project source code (like `sortedm2m_filter_horizontal_widget`).
**It is in `INSTALLED_APPS` and shadows the PyPI package, which is no longer a
dependency.**

## Why we forked

Upstream `django-image-cropping` v1.7 (Feb 2022) is unmaintained for our needs:
it bundles **Jcrop + jQuery**, its classifiers stop at **Django 4.0**, and its
workflow is "upload the image, **Save and continue editing**, scroll back up,
*then* crop" — because Jcrop crops against the already-saved file on the server.
See issue #1299 (instant preview/crop) and #1269 (de-risking dependencies ahead
of Django 6.1 LTS).

## What we changed

- **New admin widget on [Cropper.js](https://github.com/fengyuanchen/cropperjs)
  v1.6.2** (MIT, vendored as static files, no build step). It previews and
  crops the image **client-side, before the first save**. See
  `widgets.py` + `static/image_cropping/ml_cropper.js`.
- **Removed** the pluggable backend / `django-appconf` config layer; easy_thumbnails
  is wired directly.
- Dropped upstream's unused pieces for our codebase (ForeignKey-image cropping,
  the `cropped_thumbnail` template tag — Banner now uses the same
  `{% thumbnail … box=banner.cropping %}` idiom as everywhere else).

## What we deliberately kept identical

- `ImageRatioField` is still a `CharField` storing `"x1,y1,x2,y2"`, and its
  `deconstruct()` still returns `image_cropping.fields.ImageRatioField`.
  **This is a migration-safety contract** (pinned by
  `website/tests/test_image_cropping.py`): `website/migrations/` is gitignored
  and regenerated per environment, existing migration files
  `import image_cropping.fields`, and deploys are push-only with no server shell
  to repair a broken `migrate`. Keeping the package name and field path is what
  makes the swap a no-op at the database layer.
- `crop_corners` (the easy_thumbnails processor) is unchanged, so every
  `{% thumbnail … box=obj.cropping %}` call site keeps working.

## Layout

```
image_cropping/
  __init__.py              exports ImageRatioField, ImageCroppingMixin
  fields.py                ImageRatioField (+ max_cropping helper)
  thumbnail_processors.py  crop_corners (easy_thumbnails processor)
  admin.py                 ImageCroppingMixin
  widgets.py               CropImageWidget (Cropper.js)
  static/image_cropping/   cropper.min.{js,css} (vendored) + ml_cropper.{js,css}
```

## Upgrading Cropper.js

Replace `static/image_cropping/cropper.min.{js,css}` with a newer 1.x build and
re-run `collectstatic`. The glue in `ml_cropper.js` targets the Cropper.js v1
API (`getData`/`setData` in natural pixels); v2 is a web-components rewrite with
a different API and would require rewriting the glue.
