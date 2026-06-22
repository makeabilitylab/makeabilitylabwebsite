"""
Regression tests for the poster / talk preview card wiring (#840).

The open/close/focus behavior lives in
``static/website/js/thumbnailPreview.js`` (this repo has no JS test harness),
but the *server-side* markup in ``snippets/artifact_preview_link.html`` decides
what the card can contain, so that's what we pin here:

  - With a thumbnail, the "Poster"/"Talk" link becomes a popover trigger and a
    <template> carries the card (image + PDF / raw-file / Source actions).
  - The raw-file (e.g. PPTX) and Source actions appear only when those fields
    are set.
  - Without a thumbnail it degrades to the plain direct-to-PDF link.

Attaching a thumbnail: the factory artifacts carry only a *stub* PDF, so
``Artifact.save()``'s ImageMagick step can't generate a real thumbnail. We
write a valid 1x1 GIF straight to storage and point the field at it (bypassing
the field's ``upload_to``, which is only ever exercised by the PDF generator),
so easy_thumbnails has a real source for the ``{% thumbnail %}`` tag.
"""

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.loader import render_to_string

from website.tests.base import DatabaseTestCase
from website.tests.factories import PosterFactory, _GIF_1PX


class ArtifactPreviewCardTests(DatabaseTestCase):
    def _render(self, pub, orientation=None):
        ctx = {"pub": pub, "MEDIA_URL": "/media/"}
        if orientation:
            ctx["orientation"] = orientation
        return render_to_string("snippets/display_pub_snippet.html", ctx)

    def _attach_thumbnail(self, artifact):
        """
        Give ``artifact`` a real (1x1 GIF) thumbnail without re-running
        Artifact.save(): write the file via default storage at the artifact's
        own thumbnail path, then persist the field name with an UPDATE so
        easy_thumbnails can open it during template rendering.
        """
        rel_path = artifact.get_upload_thumbnail_dir(f"preview_test_{artifact.pk}.gif")
        saved_name = default_storage.save(rel_path, ContentFile(_GIF_1PX))
        type(artifact).objects.filter(pk=artifact.pk).update(thumbnail=saved_name)
        artifact.refresh_from_db()
        return artifact

    def test_thumbnail_turns_link_into_a_card_trigger(self):
        author = self.make_person()
        poster = self._attach_thumbnail(PosterFactory(authors=[author]))
        pub = self.make_publication(authors=[author], poster=poster)

        html = self._render(pub)

        # Trigger + inert template + dialog card, with the generated thumbnail.
        self.assertIn("artifact-preview-trigger", html)
        self.assertIn('aria-haspopup="dialog"', html)
        self.assertIn("artifact-preview-template", html)
        self.assertIn('role="dialog"', html)
        self.assertIn("600x0", html)  # the {% thumbnail %} variant was built
        # The PDF action and its file size are always present.
        self.assertIn("artifact-preview-action", html)
        self.assertIn("artifact-preview-size", html)

    def test_raw_file_adds_a_download_action(self):
        author = self.make_person()
        talk = self.make_talk(
            raw_file=SimpleUploadedFile(
                "slides.pptx", b"PKstub", content_type="application/octet-stream"
            )
        )
        talk = self._attach_thumbnail(talk)
        pub = self.make_publication(authors=[author], talk=talk)

        html = self._render(pub)

        self.assertIn("PPTX", html)     # raw_file_label
        # Links to the raw file. Storage may uniquify the stored name
        # (slides.pptx -> slides_xxxx.pptx) when the media dir already has one,
        # so match the extension rather than the exact filename.
        self.assertIn(".pptx", html)

    def test_source_action_when_external_slides_url_set(self):
        author = self.make_person()
        poster = self._attach_thumbnail(
            PosterFactory(
                authors=[author],
                external_slides_url="https://www.figma.com/file/abc/poster",
            )
        )
        pub = self.make_publication(authors=[author], poster=poster)

        html = self._render(pub)

        self.assertIn("Source", html)
        self.assertIn("https://www.figma.com/file/abc/poster", html)
        self.assertIn('target="_blank"', html)
        self.assertIn('rel="noopener"', html)

    def test_plain_link_when_no_thumbnail(self):
        author = self.make_person()
        poster = PosterFactory(authors=[author])  # stub PDF → no thumbnail
        pub = self.make_publication(authors=[author], poster=poster)

        html = self._render(pub)

        # Degrades to the plain download link — no trigger, no card template.
        self.assertNotIn("artifact-preview-trigger", html)
        self.assertNotIn("artifact-preview-template", html)
        self.assertIn(">Poster", html)

    def test_no_poster_link_without_poster(self):
        author = self.make_person()
        pub = self.make_publication(authors=[author])

        html = self._render(pub)

        self.assertNotIn(">Poster", html)
        self.assertNotIn("artifact-preview-trigger", html)

    def test_card_is_wired_in_horizontal_layout_too(self):
        author = self.make_person()
        poster = self._attach_thumbnail(PosterFactory(authors=[author]))
        pub = self.make_publication(authors=[author], poster=poster)

        html = self._render(pub, orientation="horizontal")

        self.assertIn("artifact-preview-trigger", html)
        self.assertIn("artifact-preview-template", html)

    def test_missing_file_degrades_instead_of_crashing(self):
        """
        Reading FileField.size stats the file and raises if it's missing on
        disk (which happens on the servers). The card renders that size for
        every entry on a listing, so a missing file must degrade to "no size"
        rather than 500 the whole page (#840).
        """
        author = self.make_person()
        poster = self._attach_thumbnail(PosterFactory(authors=[author]))
        # Simulate the PDF having gone missing on disk while the field/thumbnail
        # still point at it.
        default_storage.delete(poster.pdf_file.name)

        self.assertIsNone(poster.pdf_file_size)

        pub = self.make_publication(authors=[author], poster=poster)
        # Must not raise despite the missing file; card + PDF action still show.
        html = self._render(pub)
        self.assertIn("artifact-preview-trigger", html)
        self.assertIn("PDF", html)

    def test_safe_file_size_returns_bytes_when_present(self):
        poster = PosterFactory()  # stub PDF present on disk
        self.assertEqual(poster.pdf_file_size, len(b"%PDF-1.4 test"))
        # No raw_file → None (not a crash).
        self.assertIsNone(poster.raw_file_size)
