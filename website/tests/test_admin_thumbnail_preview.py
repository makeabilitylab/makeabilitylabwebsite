"""
Regression tests for the artifact thumbnail preview on the admin *change form*
(#1380).

``ArtifactAdmin.thumbnail_preview`` renders a read-only <img> of the artifact's
auto-generated ``thumbnail`` so editors can confirm the right PDF is attached.
``get_fieldsets`` injects it into the 'Files' fieldset on the change form (only)
for all three artifact admins (Publication / Talk / Poster).

Attaching a thumbnail: factory artifacts carry only a *stub* PDF, so
Artifact.save()'s ImageMagick step can't generate a real thumbnail. We write a
valid 1x1 GIF straight to storage and point the field at it (same trick as
test_thumbnail_preview.py for the #840 card), so easy_thumbnails has a real
source.
"""

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.urls import reverse

from website.models import Poster, Publication, Talk
from website.admin.admin_site import ml_admin_site
from website.admin.poster_admin import PosterAdmin
from website.admin.publication_admin import PublicationAdmin
from website.admin.talk_admin import TalkAdmin
from website.tests.base import DatabaseTestCase
from website.tests.factories import PosterFactory, _GIF_1PX


class ArtifactThumbnailPreviewTests(DatabaseTestCase):
    def _attach_thumbnail(self, artifact):
        """Give ``artifact`` a real (1x1 GIF) thumbnail without re-running
        Artifact.save(): write the file via default storage at the artifact's
        own thumbnail path, then persist the field name with an UPDATE."""
        rel_path = artifact.get_upload_thumbnail_dir(f"admin_preview_{artifact.pk}.gif")
        saved_name = default_storage.save(rel_path, ContentFile(_GIF_1PX))
        type(artifact).objects.filter(pk=artifact.pk).update(thumbnail=saved_name)
        artifact.refresh_from_db()
        return artifact

    def test_preview_renders_img_when_thumbnail_present(self):
        poster = self._attach_thumbnail(PosterFactory(authors=[self.make_person()]))
        admin = PosterAdmin(Poster, ml_admin_site)

        html = admin.thumbnail_preview(poster)

        self.assertIn("<img", html)
        self.assertIn(default_storage.url(poster.thumbnail.name).rsplit("/", 1)[0], html)
        self.assertIn("height:220px", html)

    def test_preview_is_placeholder_when_no_thumbnail(self):
        poster = PosterFactory(authors=[self.make_person()])  # stub PDF → no thumbnail
        admin = PosterAdmin(Poster, ml_admin_site)

        html = admin.thumbnail_preview(poster)

        self.assertNotIn("<img", html)
        self.assertIn("Save with a PDF", html)

    def test_preview_degrades_when_source_file_missing(self):
        """Thumbnail field set but the file is gone from disk (happens on the
        servers) → placeholder, not a 500."""
        poster = self._attach_thumbnail(PosterFactory(authors=[self.make_person()]))
        default_storage.delete(poster.thumbnail.name)

        admin = PosterAdmin(Poster, ml_admin_site)
        html = admin.thumbnail_preview(poster)

        self.assertNotIn("<img", html)
        self.assertIn("Save with a PDF", html)

    def test_preview_handles_none_obj(self):
        admin = PosterAdmin(Poster, ml_admin_site)
        # get_fieldsets passes the saved obj, but be defensive.
        self.assertIn("Save with a PDF", admin.thumbnail_preview(None))

    def _files_fields(self, admin, obj):
        for name, opts in admin.get_fieldsets(request=None, obj=obj):
            if name == "Files":
                return list(opts.get("fields", []))
        return []

    def test_get_fieldsets_injects_preview_on_change_for_all_admins(self):
        cases = (
            (PublicationAdmin, Publication, self.make_publication()),
            (TalkAdmin, Talk, self.make_talk()),
            (PosterAdmin, Poster, PosterFactory(authors=[self.make_person()])),
        )
        for admin_cls, model, obj in cases:
            admin = admin_cls(model, ml_admin_site)
            change_fields = self._files_fields(admin, obj)
            self.assertIn(
                "thumbnail_preview", change_fields,
                f"{admin_cls.__name__} change form should show the preview",
            )

    def test_get_fieldsets_omits_preview_on_add(self):
        admin = PublicationAdmin(Publication, ml_admin_site)
        add_fields = self._files_fields(admin, obj=None)
        self.assertNotIn("thumbnail_preview", add_fields)

    def test_change_form_get_renders_img_end_to_end(self):
        """Full change-form GET through the admin: the readonly preview must
        render the <img> as real (unescaped) HTML, not as escaped text."""
        poster = self._attach_thumbnail(PosterFactory(authors=[self.make_person()]))
        User.objects.create_superuser("admin", "admin@example.com", "pw")
        self.client.force_login(User.objects.get(username="admin"))

        url = reverse("admin:website_poster_change", args=[poster.pk])
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode()
        self.assertIn('alt="Thumbnail preview"', body)
        self.assertIn("<img", body)
        # The tag is real markup, not escaped into visible text.
        self.assertNotIn("&lt;img", body)

    def test_get_fieldsets_does_not_mutate_class_fieldsets(self):
        """Injecting the preview must not leak into the shared class-level
        fieldsets (which would compound across requests)."""
        admin = TalkAdmin(Talk, ml_admin_site)
        admin.get_fieldsets(request=None, obj=self.make_talk())
        for name, opts in TalkAdmin.fieldsets:
            if name == "Files":
                self.assertNotIn("thumbnail_preview", opts["fields"])
