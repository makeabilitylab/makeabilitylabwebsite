"""
Regression tests for the django-ckeditor -> django-prose-editor migration (#1269):

- `News.content` (ProseEditorField, sanitize=True) preserves our real markup and
  drops only `style` on `<img>` when it sanitizes.
- the staff-only image upload picker view (auth gate, CKEditor-protocol callback,
  rejection of non-image payloads), and
- the `normalize_news_image_styles` command that makes legacy images responsive.
"""

import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse

from website.models import News
from website.management.commands.normalize_news_image_styles import (
    normalize_image_dimensions,
)
from website.tests.base import DatabaseTestCase
from website.tests.factories import _GIF_1PX

# Representative legacy News body covering every tag our 51-post production audit
# found, plus an image carrying the CKEditor-style inline dimensions we want gone.
LEGACY_HTML = (
    "<h2>Big news</h2>"
    "<p>Congrats to <strong>Chu</strong> and <em>Jared</em>! "
    '<a href="https://example.com/x" target="_blank" rel="noopener">Read more</a>.</p>'
    "<ul><li>One</li><li>Two</li></ul>"
    "<blockquote>A quote.</blockquote>"
    "<p><code>pip install x</code></p>"
    '<img alt="Chu presenting" src="/media/uploads/2024/01/01/CHU.JPG" '
    'style="width:100%;height:300px" width="600" height="300" />'
)

_TMP_MEDIA = tempfile.mkdtemp()


def tearDownModule():
    shutil.rmtree(_TMP_MEDIA, ignore_errors=True)


class NewsContentSanitizeTests(DatabaseTestCase):
    """The ProseEditorField sanitizer (extension-derived nh3 allowlist)."""

    def _sanitize(self, html):
        news = self.make_news_item()
        return News._meta.get_field("content").clean(html, news)

    def test_preserves_rich_markup(self):
        out = self._sanitize(LEGACY_HTML)
        # Structure and text survive.
        self.assertIn("<h2>Big news</h2>", out)
        self.assertIn("<strong>Chu</strong>", out)
        self.assertIn("<em>Jared</em>", out)
        self.assertIn("<li>One</li>", out)
        self.assertIn("<blockquote>", out)
        self.assertIn("<code>pip install x</code>", out)
        # Links keep href and target.
        self.assertIn('href="https://example.com/x"', out)
        self.assertIn('target="_blank"', out)
        # The image itself (src/alt) survives.
        self.assertIn('src="/media/uploads/2024/01/01/CHU.JPG"', out)
        self.assertIn('alt="Chu presenting"', out)

    def test_drops_inline_style_on_images(self):
        out = self._sanitize(LEGACY_HTML)
        # The Image extension allows src/alt/width/height but NOT style, so the
        # inline style="width:100%;height:300px" is removed.
        self.assertNotIn("style=", out)


class NewsImageUploadViewTests(DatabaseTestCase):
    """The staff-only picker view wired to prose-editor's Figure pickerUrl."""

    def setUp(self):
        self.url = reverse("website:news_image_upload")
        User = get_user_model()
        self.staff = User.objects.create_user(
            username="editor", password="pw", is_staff=True
        )

    def test_requires_staff(self):
        # Anonymous users are redirected to the admin login, not served the form.
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/admin/login", resp["Location"])

    def test_get_renders_form_with_func_num(self):
        self.client.force_login(self.staff)
        resp = self.client.get(self.url, {"CKEditorFuncNum": "7"})
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode()
        self.assertIn('name="upload"', body)
        self.assertIn('name="alt_text"', body)
        self.assertIn('value="7"', body)  # round-tripped func num

    @override_settings(MEDIA_ROOT=_TMP_MEDIA)
    def test_post_saves_and_calls_back(self):
        self.client.force_login(self.staff)
        upload = SimpleUploadedFile("photo.gif", _GIF_1PX, content_type="image/gif")
        resp = self.client.post(
            self.url,
            {"CKEditorFuncNum": "7", "alt_text": "A description", "upload": upload},
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode()
        # Calls the CKEditor-protocol callback with the func num + saved URL.
        self.assertIn("callFunction", body)
        self.assertIn("/uploads/", body)
        self.assertIn("PHOTO.GIF", body)  # get_ckeditor_image_filename uppercases
        self.assertIn("A description", body)

    @override_settings(MEDIA_ROOT=_TMP_MEDIA)
    def test_rejects_non_image_payload(self):
        self.client.force_login(self.staff)
        evil = SimpleUploadedFile(
            "evil.svg", b"<svg onload=alert(1)></svg>", content_type="image/svg+xml"
        )
        resp = self.client.post(
            self.url, {"CKEditorFuncNum": "7", "upload": evil}
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode()
        self.assertNotIn("callFunction", body)  # no insertion happened
        self.assertIn("upload", body)  # re-rendered the form


class NewsAdminWidgetTests(DatabaseTestCase):
    """The News admin renders the prose-editor widget wired to our upload view."""

    def test_admin_add_page_renders_prose_editor(self):
        User = get_user_model()
        boss = User.objects.create_superuser("boss", "boss@example.com", "pw")
        self.client.force_login(boss)
        resp = self.client.get(reverse("admin:website_news_add"))
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode()
        # The ProseEditorField widget injects its static assets via Media...
        self.assertIn("django_prose_editor", body)
        # ...and the Figure pickerUrl points at our staff-only upload view.
        self.assertIn(reverse("website:news_image_upload"), body)


class NormalizeNewsImageStylesTests(DatabaseTestCase):
    """The idempotent legacy-image normalizer (command + transform fn)."""

    def test_transform_strips_dimensions_preserves_markup(self):
        out = normalize_image_dimensions(LEGACY_HTML)
        # All inline dimensions gone (style decls AND width/height attributes).
        self.assertNotIn("style=", out)
        self.assertNotIn("width=", out)
        self.assertNotIn("height=", out)
        self.assertNotIn("width:", out)
        # The image and the rest of the markup are untouched.
        self.assertIn('src="/media/uploads/2024/01/01/CHU.JPG"', out)
        self.assertIn('alt="Chu presenting"', out)
        self.assertIn('href="https://example.com/x"', out)
        self.assertIn("<blockquote>", out)

    def test_transform_is_idempotent(self):
        once = normalize_image_dimensions(LEGACY_HTML)
        twice = normalize_image_dimensions(once)
        self.assertEqual(once, twice)

    def test_command_updates_rows(self):
        # Factory create() saves without full_clean, so the raw legacy HTML
        # (with inline dimensions) persists, mimicking a pre-migration row.
        news = self.make_news_item(content=LEGACY_HTML)
        call_command("normalize_news_image_styles")
        news.refresh_from_db()
        self.assertNotIn("style=", news.content)
        self.assertNotIn("width=", news.content)
        self.assertIn('src="/media/uploads/2024/01/01/CHU.JPG"', news.content)
