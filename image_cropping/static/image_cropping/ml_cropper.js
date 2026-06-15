/**
 * ml_cropper.js — client-side image cropping for the Django admin (#1299).
 *
 * Replaces the old Jcrop/jQuery widget from django-image-cropping. For each
 * crop field it:
 *   1. finds the sibling <input type="file"> for the image being cropped;
 *   2. shows an INSTANT preview the moment a file is selected (via
 *      URL.createObjectURL) — no "Save and continue editing" round-trip;
 *   3. runs Cropper.js locked to the field's aspect ratio;
 *   4. writes the selection back as an "x1,y1,x2,y2" box (original-image
 *      pixels) into the ratio field that the server persists.
 *
 * Coordinates are read from Cropper's getData(), which is already in natural
 * image pixels, so they map directly onto the stored original and onto the
 * easy_thumbnails `crop_corners` processor — no scaling math, no baked file.
 *
 * Accessibility: alongside the drag UI, each cropper exposes labeled numeric
 * X / Y / Width / Height inputs that are fully keyboard-operable and kept in
 * sync with the visual crop box. With JS off, the raw ratio field still
 * submits and the server seeds a sensible centered crop.
 *
 * Vanilla JS only (no jQuery/build step), per project conventions.
 */
(function () {
  "use strict";

  if (typeof window.Cropper === "undefined") {
    // Cropper.js failed to load; leave the raw ratio field in place so the
    // form still works (server seeds a default crop on save).
    return;
  }

  /** Parse "x1,y1,x2,y2" -> {x, y, width, height} or null. */
  function parseBox(value) {
    if (!value) return null;
    var p = value.split(",").map(function (n) { return parseInt(n, 10); });
    if (p.length !== 4 || p.some(isNaN)) return null;
    return { x: p[0], y: p[1], width: p[2] - p[0], height: p[3] - p[1] };
  }

  /** Format Cropper getData() -> "x1,y1,x2,y2" with clamped integers. */
  function formatBox(data, naturalWidth, naturalHeight) {
    var x1 = Math.max(0, Math.round(data.x));
    var y1 = Math.max(0, Math.round(data.y));
    var x2 = Math.min(naturalWidth, Math.round(data.x + data.width));
    var y2 = Math.min(naturalHeight, Math.round(data.y + data.height));
    return [x1, y1, x2, y2].join(",");
  }

  /**
   * Locate the file input paired with a ratio field. Both share the form
   * prefix (e.g. inline "banner_set-0-"), differing only in the trailing
   * field name: "...-cropping" -> "...-image".
   */
  function findImageInput(ratioInput, myName, imageFieldName) {
    var name = ratioInput.getAttribute("name") || "";
    if (name.slice(-myName.length) !== myName) return null;
    var imageName = name.slice(0, name.length - myName.length) + imageFieldName;
    var form = ratioInput.closest("form") || document;
    return form.querySelector('[name="' + imageName + '"]');
  }

  function makeNumberInput(label, idBase, key) {
    var wrap = document.createElement("label");
    wrap.className = "ml-cropper__num";
    wrap.textContent = label + " ";
    var input = document.createElement("input");
    input.type = "number";
    input.min = "0";
    input.step = "1";
    input.id = idBase + "_" + key;
    input.className = "ml-cropper__num-input";
    input.setAttribute("data-key", key);
    wrap.appendChild(input);
    return { wrap: wrap, input: input };
  }

  function setupField(ratioInput) {
    if (ratioInput.dataset.mlCropperReady === "1") return;
    ratioInput.dataset.mlCropperReady = "1";

    var imageFieldName = ratioInput.getAttribute("data-image-field");
    var myName = ratioInput.getAttribute("data-my-name") || "";
    var ratioAttr = parseFloat(ratioInput.getAttribute("data-ratio"));
    var aspectRatio = ratioAttr > 0 ? ratioAttr : NaN; // NaN => free crop
    var minWidth = parseInt(ratioInput.getAttribute("data-min-width"), 10) || 0;
    var minHeight = parseInt(ratioInput.getAttribute("data-min-height"), 10) || 0;
    var sizeWarning = ratioInput.getAttribute("data-size-warning") === "true";

    var fileInput = findImageInput(ratioInput, myName, imageFieldName);
    if (!fileInput) return;

    // Hide the raw "x1,y1,x2,y2" text box (kept in the DOM as the value holder)
    // and its label row; the cropper UI replaces it visually.
    var ratioRow = ratioInput.closest(".form-row, .field-" + myName) || ratioInput.parentNode;
    if (ratioRow) ratioRow.classList.add("ml-cropper__hidden-row");

    // Build the cropper UI under the file input's row.
    var idBase = "ml_cropper_" + (ratioInput.id || myName);
    var container = document.createElement("div");
    container.className = "ml-cropper";

    var stage = document.createElement("div");
    stage.className = "ml-cropper__stage";
    var img = document.createElement("img");
    img.className = "ml-cropper__image";
    img.alt = "Crop preview";
    stage.appendChild(img);
    container.appendChild(stage);

    // Live WYSIWYG preview: shows exactly what the cropped thumbnail will look
    // like. Cropper.js fills the preview box's width with the selected crop, so
    // we size the box to the field's aspect ratio for a true-to-output preview.
    var previewWrap = document.createElement("div");
    previewWrap.className = "ml-cropper__preview-wrap";
    var previewLabel = document.createElement("span");
    previewLabel.className = "ml-cropper__preview-label";
    previewLabel.textContent = "Preview";
    var preview = document.createElement("div");
    preview.className = "ml-cropper__preview";
    var previewW = 160;
    preview.style.width = previewW + "px";
    preview.style.height =
      Math.round(previewW / (aspectRatio > 0 ? aspectRatio : 1)) + "px";
    previewWrap.appendChild(previewLabel);
    previewWrap.appendChild(preview);
    container.appendChild(previewWrap);

    var warning = document.createElement("p");
    warning.className = "ml-cropper__warning";
    warning.setAttribute("role", "alert");
    warning.hidden = true;
    container.appendChild(warning);

    // Precise, keyboard-accessible numeric controls, tucked into a collapsed
    // disclosure: they stay out of the way of the common drag-to-crop flow but
    // remain reachable for keyboard / screen-reader users who need exact values.
    var advanced = document.createElement("details");
    advanced.className = "ml-cropper__advanced";
    var summary = document.createElement("summary");
    summary.className = "ml-cropper__summary";
    summary.textContent = "Adjust crop precisely (pixels)";
    advanced.appendChild(summary);
    var controls = document.createElement("div");
    controls.className = "ml-cropper__controls";
    var nums = {
      x: makeNumberInput("X", idBase, "x"),
      y: makeNumberInput("Y", idBase, "y"),
      width: makeNumberInput("Width", idBase, "width"),
      height: makeNumberInput("Height", idBase, "height"),
    };
    Object.keys(nums).forEach(function (k) { controls.appendChild(nums[k].wrap); });
    advanced.appendChild(controls);
    container.appendChild(advanced);

    var fileRow = fileInput.closest(".form-row, .field-" + imageFieldName) || fileInput.parentNode;
    fileRow.parentNode.insertBefore(container, fileRow.nextSibling);

    var cropper = null;
    var syncing = false; // guard against crop<->numeric feedback loops
    var pendingBox = parseBox(ratioInput.value); // existing crop to restore
    var currentObjectUrl = null; // blob: URL of the currently previewed file

    function updateWarning(data) {
      if (!sizeWarning) return;
      var tooSmall = data.width < minWidth || data.height < minHeight;
      if (tooSmall) {
        warning.hidden = false;
        warning.textContent =
          "Heads up: this crop (" + Math.round(data.width) + "×" +
          Math.round(data.height) + " px) is smaller than the recommended " +
          minWidth + "×" + minHeight + " px and may look soft when enlarged.";
      } else {
        warning.hidden = true;
      }
    }

    function onCrop() {
      if (!cropper || syncing) return;
      var data = cropper.getData();
      var img2 = cropper.getImageData();
      ratioInput.value = formatBox(data, img2.naturalWidth, img2.naturalHeight);
      syncing = true;
      nums.x.input.value = Math.round(data.x);
      nums.y.input.value = Math.round(data.y);
      nums.width.input.value = Math.round(data.width);
      nums.height.input.value = Math.round(data.height);
      syncing = false;
      updateWarning(data);
    }

    function applyNumbers() {
      if (!cropper || syncing) return;
      syncing = true;
      cropper.setData({
        x: parseFloat(nums.x.input.value) || 0,
        y: parseFloat(nums.y.input.value) || 0,
        width: parseFloat(nums.width.input.value) || minWidth,
        height: parseFloat(nums.height.input.value) || minHeight,
      });
      syncing = false;
      onCrop();
    }
    Object.keys(nums).forEach(function (k) {
      nums[k].input.addEventListener("change", applyNumbers);
    });

    function initCropper(src, restoreBox) {
      if (cropper) { cropper.destroy(); cropper = null; }
      pendingBox = restoreBox || null;
      img.src = src;
      stage.classList.add("ml-cropper__stage--active");
    }

    img.addEventListener("load", function () {
      if (cropper) { cropper.destroy(); cropper = null; }
      cropper = new window.Cropper(img, {
        aspectRatio: aspectRatio,
        viewMode: 1,
        autoCropArea: 1,
        responsive: true,
        preview: preview, // live thumbnail of the cropped result
        // Keep the on-screen pixels identical to what the server crops:
        // easy_thumbnails / Pillow crop_corners operates on the raw stored
        // image without applying EXIF orientation, so the cropper must show
        // the same un-rotated pixels. (checkOrientation:true also stalls on
        // blob: object URLs from a just-picked file, which is the instant
        // preview path.)
        checkOrientation: false,
        background: true,
        ready: function () {
          if (pendingBox) {
            syncing = true;
            cropper.setData(pendingBox);
            syncing = false;
            pendingBox = null;
          }
          onCrop();
        },
        crop: onCrop,
      });
    });

    // INSTANT preview: crop straight from the just-picked file, pre-upload.
    // Keep the object URL alive for the whole crop session — Cropper.js builds
    // its live preview clone from this same URL *after* the main image loads,
    // so revoking on load would leave the preview blank. Revoke the previous
    // URL only when a new file replaces it (the last one is freed on unload).
    fileInput.addEventListener("change", function () {
      var file = fileInput.files && fileInput.files[0];
      if (!file) return;
      if (currentObjectUrl) URL.revokeObjectURL(currentObjectUrl);
      currentObjectUrl = URL.createObjectURL(file);
      initCropper(currentObjectUrl, null);
    });

    // Existing image (edit page): load the full-res original for re-cropping.
    var originalUrl = fileInput.getAttribute("data-original-url");
    if (originalUrl) {
      initCropper(originalUrl, parseBox(ratioInput.value));
    }
  }

  function scan(root) {
    (root || document).querySelectorAll("input.image-ratio").forEach(setupField);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { scan(document); });
  } else {
    scan(document);
  }

  // Newly added inline rows (Django dispatches a native formset:added event).
  document.addEventListener("formset:added", function (event) {
    scan(event.target || document);
  });
})();
