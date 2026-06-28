/**
 * pad_to_square.js — "pad to square" preview for the Award badge admin (#1410).
 *
 * The badge is cropped to a 1:1 square on the public Awards page (via
 * image_cropping + Cropper.js). For a non-square logo, cropping chops off
 * content, so AwardAdminForm offers a "Pad badge to a square (don't crop)"
 * checkbox: when checked, the server pads the upload with white/transparent
 * margins (see website.utils.fileutils.pad_image_to_square) instead of cropping.
 *
 * This script keeps the admin honest about that choice WITHOUT re-implementing
 * the padding in the browser (which would mean a fiddly canvas + file-swap
 * dance). Instead:
 *   - When "pad" is checked, the interactive cropper is hidden (there is
 *     nothing to crop) and we show a faithful preview using CSS
 *     `object-fit: contain` — which letterboxes the image inside a square box
 *     exactly the way the server pads it (centered, equal margins).
 *   - When unchecked, the cropper returns and behaves as before.
 *
 * Hiding the cropper is done purely by toggling a `pad-mode` class on the form
 * (see pad_to_square.css), so there's no ordering dependency on ml_cropper.js
 * building its widget first — the CSS rule applies whenever that widget exists.
 *
 * Vanilla JS only (no jQuery / build step), per project conventions. Scoped to
 * the badge field by name; to reuse elsewhere, parameterize the two constants.
 */
(function () {
  "use strict";

  var CHECKBOX_NAME = "pad_badge_to_square";
  var FILE_NAME = "badge";

  /**
   * PNG/WebP/GIF can carry alpha, so their padded margins are transparent;
   * JPEG can't, so its margins are white. We sniff the picked file's MIME type
   * (or fall back to the existing image's URL/extension) to mirror that in the
   * preview's background.
   */
  function isTransparentFormat(file, fallbackUrl) {
    var s = ((file && file.type) || fallbackUrl || "").toLowerCase();
    return /png|webp|gif/.test(s);
  }

  function setup(checkbox) {
    var form = checkbox.closest("form") || document;
    var fileInput = form.querySelector('[name="' + FILE_NAME + '"]');
    if (!fileInput) return;

    // Build the padded-square preview once, just after the file input's row.
    var fileRow =
      fileInput.closest(".form-row, .field-" + FILE_NAME) || fileInput.parentNode;
    var preview = document.createElement("div");
    preview.className = "pad-preview";
    preview.innerHTML =
      '<span class="pad-preview__label">Preview (padded to a square)</span>' +
      '<div class="pad-preview__box"><img class="pad-preview__img" alt=""></div>' +
      '<p class="pad-preview__note"></p>';
    fileRow.parentNode.insertBefore(preview, fileRow.nextSibling);

    var box = preview.querySelector(".pad-preview__box");
    var imgEl = preview.querySelector(".pad-preview__img");
    var note = preview.querySelector(".pad-preview__note");
    var objectUrl = null;
    var originalUrl = fileInput.getAttribute("data-original-url");

    function showImage(src, transparent) {
      if (!src) {
        imgEl.removeAttribute("src");
        note.textContent = "Upload a badge to preview it.";
        return;
      }
      imgEl.src = src;
      box.classList.toggle("pad-preview__box--checker", transparent);
      note.textContent = transparent
        ? "Transparent margins are added (checkerboard = transparent)."
        : "White margins are added.";
    }

    // Seed from an existing badge on the edit page, if any.
    showImage(originalUrl || null, isTransparentFormat(null, originalUrl));

    fileInput.addEventListener("change", function () {
      var file = fileInput.files && fileInput.files[0];
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
        objectUrl = null;
      }
      if (file) {
        objectUrl = URL.createObjectURL(file);
        showImage(objectUrl, isTransparentFormat(file, file.name));
      } else {
        showImage(originalUrl || null, isTransparentFormat(null, originalUrl));
      }
    });

    function sync() {
      form.classList.toggle("pad-mode", checkbox.checked);
    }
    checkbox.addEventListener("change", sync);
    sync();
  }

  function init() {
    document
      .querySelectorAll(
        'input[type="checkbox"][name="' + CHECKBOX_NAME + '"]'
      )
      .forEach(setup);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
