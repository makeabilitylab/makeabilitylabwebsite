"""
Regression tests for the artifact admin upload guard (issue #248).

The user-facing behavior — blocking a file-losing submit, drag-and-drop — lives
in ``website/static/website/js/admin_artifact_form.js`` and can't be exercised
from Python. What we *can* pin here is the server-side contract that JS depends
on, and which would silently break the whole feature if it regressed:

  1. Every artifact add form (Talk / Poster / Publication) loads the guard's
     JS and CSS.
  2. The file inputs carry an ``accept`` attribute derived from the same
     extension allowlists the server validators enforce — the single source of
     truth the client-side extension check reads back from the DOM.
"""

from django.contrib.auth.models import User

from website.tests.base import DatabaseTestCase
from website.utils.upload_validators import PDF_EXTENSIONS, RAW_FILE_EXTENSIONS

JS_PATH = "website/js/admin_artifact_form.js"
CSS_PATH = "website/css/admin_artifact_form.css"

PDF_ACCEPT = ",".join("." + e for e in PDF_EXTENSIONS)
RAW_ACCEPT = ",".join("." + e for e in RAW_FILE_EXTENSIONS)


class ArtifactAdminUploadGuardTests(DatabaseTestCase):
    def setUp(self):
        User.objects.create_superuser("guard_admin", "g@example.com", "pw12345!")
        self.client.login(username="guard_admin", password="pw12345!")

    def _get_add_form(self, model):
        resp = self.client.get(f"/admin/website/{model}/add/")
        self.assertEqual(resp.status_code, 200)
        return resp.content.decode()

    def test_assets_loaded_on_all_artifact_add_forms(self):
        for model in ("talk", "poster", "publication"):
            html = self._get_add_form(model)
            self.assertIn(JS_PATH, html, f"{model} add form is missing the guard JS")
            self.assertIn(CSS_PATH, html, f"{model} add form is missing the guard CSS")

    def test_pdf_file_accept_matches_validator_allowlist(self):
        for model in ("talk", "poster", "publication"):
            html = self._get_add_form(model)
            self.assertIn(f'accept="{PDF_ACCEPT}"', html,
                          f"{model} pdf_file input is missing the expected accept attribute")

    def test_raw_file_accept_matches_validator_allowlist(self):
        # Talk and Poster expose raw_file; Publication intentionally does not.
        for model in ("talk", "poster"):
            html = self._get_add_form(model)
            self.assertIn(f'accept="{RAW_ACCEPT}"', html,
                          f"{model} raw_file input is missing the expected accept attribute")
