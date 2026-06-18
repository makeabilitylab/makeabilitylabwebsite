"""
Staff-only image upload endpoint for the News rich-text editor (issue #1269).

django-prose-editor's Figure extension opens this URL in a popup as a file
"picker" using the CKEditor 4 filebrowser protocol: the editor appends
``?CKEditorFuncNum=N`` to the URL, and the popup is expected to call
``window.opener.CKEDITOR.tools.callFunction(N, url, {alternative_text})`` once a
file has been chosen. django-prose-editor ships a small shim that registers that
callback, so no actual CKEditor install is involved (see the Figure extension /
``pickerUrl`` config on website/models/news.py).

This preserves the upload behavior we had under CKEditor: files land in
``MEDIA_ROOT/uploads/YYYY/MM/DD/`` with names produced by
``get_ckeditor_image_filename``, so the filename convention and historical
``/media/uploads/...`` URLs are unchanged. Uploads are validated with
``validate_image_upload`` (extension allowlist + magic-byte sniff that rejects
SVG/HTML), the same defense-in-depth used on other media fields. The callback
returns only the URL (no width/height), so inserted images carry no inline
dimensions and the responsive ``.news-item-content img`` CSS governs sizing.

Example flow (admin only):
    GET  /news/upload-image/?CKEditorFuncNum=12   -> renders the upload form
    POST /news/upload-image/  (multipart: upload, alt_text, CKEditorFuncNum)
        -> saves the file, renders a page that calls the editor callback
"""

import os

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from website.utils.fileutils import get_ckeditor_image_filename
from website.utils.upload_validators import validate_image_upload

__all__ = ["news_image_upload"]

_TEMPLATE = "website/news_image_picker.html"


@staff_member_required
@require_http_methods(["GET", "POST"])
def news_image_upload(request):
    """Render the picker form (GET) or save an upload and call the editor back (POST)."""
    # The editor passes CKEditorFuncNum on the initial GET; we round-trip it
    # through the form so the success page can call back the right function.
    func_num = (
        request.GET.get("CKEditorFuncNum")
        or request.POST.get("CKEditorFuncNum")
        or ""
    )

    if request.method == "GET":
        return render(request, _TEMPLATE, {"func_num": func_num})

    upload = request.FILES.get("upload")
    alt_text = (request.POST.get("alt_text") or "").strip()

    error = None
    if not upload:
        error = "Please choose an image file to upload."
    else:
        try:
            validate_image_upload(upload)
        except ValidationError as exc:
            error = " ".join(exc.messages)

    if error:
        return render(request, _TEMPLATE, {"func_num": func_num, "error": error})

    # Mirror the old CKEditor upload layout: media/uploads/YYYY/MM/DD/<name>.
    today = timezone.localdate()
    name = get_ckeditor_image_filename(upload.name)
    rel_path = os.path.join(
        "uploads", f"{today:%Y}", f"{today:%m}", f"{today:%d}", name
    )
    saved_path = default_storage.save(rel_path, upload)  # auto-uniquifies on collision
    url = default_storage.url(saved_path)

    return render(
        request,
        _TEMPLATE,
        {"func_num": func_num, "uploaded_url": url, "alt_text": alt_text},
    )
