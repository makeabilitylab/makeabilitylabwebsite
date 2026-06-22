/**
 * Client-side guard + drag-and-drop for the artifact (Talk / Poster / Publication)
 * admin add/change forms. Addresses issue #248.
 *
 * Why this exists
 * ---------------
 * The Django admin renders its change form with the `novalidate` attribute, which
 * disables the browser's native HTML5 constraint validation. So even though Django
 * emits `required` on every form-required field, the browser does NOT block a submit
 * that's missing one. The POST goes to the server, validation fails, the form is
 * re-rendered with errors — and any file the user had selected is silently dropped
 * (the browser never re-sends a file input's value, and Django can't repopulate it).
 * Re-uploading the lost PDF/PPTX after fixing an unrelated required field is the
 * exact pain reported in #248.
 *
 * What this does (all progressive enhancement — the form still works without JS):
 *   1. Required-field guard: on submit, blocks the POST if any required field is
 *      empty, shows an accessible summary, and scrolls to the first offender — so
 *      the round-trip that loses files never happens.
 *   2. File pre-checks: on selection, validates extension (against the field's
 *      `accept` list) and, for PDF-only fields, the `%PDF-` signature — mirroring
 *      the server validators so a bad file is caught before it costs a round-trip.
 *   3. A standard drag-and-drop upload zone per file field: the raw file input is
 *      hidden (but kept focusable), the zone is the primary control with idle /
 *      hover / drag-over / filled / error states, and the selected file is shown
 *      with its name, size, and a Remove/Replace control.
 *
 * Accessibility: the native <input type=file> stays in the DOM, focusable, and
 * keeps its <label> association — it is the control assistive tech uses. The zone
 * is a mouse/visual layer (aria-hidden); it mirrors the input's focus with a ring
 * so keyboard users get a visible focus state, and error state is never color-only.
 *
 * Staying in sync with the backend (see also website/utils/upload_validators.py):
 *   - Required-ness is read from the DOM (`[required]`), which Django derives from
 *     each model field's `blank=`. No field list is hardcoded here.
 *   - Allowed extensions are read from each file input's `accept` attribute, which
 *     ArtifactAdmin.get_form sets from the same PDF_EXTENSIONS / RAW_FILE_EXTENSIONS
 *     constants the server validators use. Python is the single source of truth.
 *   - The `%PDF-` signature is a frozen part of the PDF spec (mirrors
 *     _looks_like_pdf in upload_validators.py), so there is nothing to keep in sync.
 *
 * The server validators remain authoritative; everything here is a convenience
 * pre-check, so any drift degrades gracefully (at worst a redundant round-trip).
 */
(function () {
  "use strict";

  // How many leading bytes to sniff for the PDF signature (matches the server's
  // _read_header default in upload_validators.py).
  var PDF_HEADER_BYTES = 1024;

  // Inline icons (no external assets / build step). currentColor follows the zone.
  var UPLOAD_SVG =
    '<svg class="artifact-dropzone-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">' +
    '<path fill="currentColor" d="M12 3l5.5 5.5-1.42 1.42L13 6.83V16h-2V6.83L8.92 9.92 7.5 8.5 12 3zM5 18h14v2H5z"/></svg>';
  var FILE_SVG =
    '<svg class="artifact-dropzone-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">' +
    '<path fill="currentColor" d="M6 2h7l5 5v15H6V2zm7 1.5V8h4.5L13 3.5z"/></svg>';

  /**
   * The main artifact form: the multipart add/change form. Returns null on any
   * other admin page (this script is only loaded on the artifact admins anyway).
   * @returns {HTMLFormElement|null}
   */
  function getArtifactForm() {
    return document.querySelector('#content-main form[enctype="multipart/form-data"]');
  }

  /**
   * Human-readable label for a form control, taken from its <label>, with the
   * trailing colon and required asterisk stripped. Falls back to the field name.
   * @param {HTMLElement} el
   * @returns {string}
   */
  function labelFor(el) {
    var label = el.id ? document.querySelector('label[for="' + el.id + '"]') : null;
    var text = label ? label.textContent : (el.getAttribute("name") || "This field");
    return text.replace(/[:*\s]+$/, "").trim();
  }

  /**
   * Whether a required control has no value yet.
   * @param {HTMLElement} el
   * @returns {boolean}
   */
  function isEmpty(el) {
    if (el.type === "file") {
      return !el.files || el.files.length === 0;
    }
    return !el.value || !String(el.value).trim();
  }

  /**
   * Allowed extensions (lowercase, no dot) parsed from a file input's `accept`
   * attribute, e.g. ".pdf,.pptx" -> ["pdf", "pptx"]. Empty array if unset.
   * @param {HTMLInputElement} input
   * @returns {string[]}
   */
  function allowedExtensions(input) {
    var accept = input.getAttribute("accept");
    if (!accept) return [];
    return accept
      .split(",")
      .map(function (s) { return s.trim().replace(/^\./, "").toLowerCase(); })
      .filter(Boolean);
  }

  /** Lowercase extension (no dot) of a filename. */
  function extensionOf(name) {
    var dot = name.lastIndexOf(".");
    return dot === -1 ? "" : name.slice(dot + 1).toLowerCase();
  }

  /** Short accepted-types hint from the input's accept list, e.g. "PDF only". */
  function acceptHint(input) {
    var exts = allowedExtensions(input);
    if (!exts.length) return "";
    if (exts.length === 1) return exts[0].toUpperCase() + " only";
    return exts.map(function (e) { return e.toUpperCase(); }).join(", ");
  }

  /** Human-readable file size, e.g. "128 KB" / "3.4 MB". */
  function humanFileSize(bytes) {
    if (typeof bytes !== "number") return "";
    if (bytes < 1024) return bytes + " B";
    var kb = bytes / 1024;
    if (kb < 1024) return (kb < 10 ? kb.toFixed(1) : Math.round(kb)) + " KB";
    return (kb / 1024).toFixed(1) + " MB";
  }

  /**
   * Read the first `numBytes` of a File as a Uint8Array (resolves null on error).
   * @param {File} file
   * @param {number} numBytes
   * @returns {Promise<Uint8Array|null>}
   */
  function readHeader(file, numBytes) {
    return new Promise(function (resolve) {
      var reader = new FileReader();
      reader.onload = function () { resolve(new Uint8Array(reader.result)); };
      reader.onerror = function () { resolve(null); };
      reader.readAsArrayBuffer(file.slice(0, numBytes));
    });
  }

  /** True if `bytes` contains the ASCII "%PDF-" signature. */
  function looksLikePdf(bytes) {
    if (!bytes) return true; // unreadable -> don't block; let the server decide
    var sig = "%PDF-";
    var text = "";
    for (var i = 0; i < bytes.length; i++) text += String.fromCharCode(bytes[i]);
    return text.indexOf(sig) !== -1;
  }

  /**
   * Validate a freshly selected file against the field's rules. Resolves to an
   * error string, or "" if the file is acceptable.
   * @param {HTMLInputElement} input
   * @returns {Promise<string>}
   */
  function validateFile(input) {
    if (!input.files || input.files.length === 0) return Promise.resolve("");
    var file = input.files[0];
    var allowed = allowedExtensions(input);
    var ext = extensionOf(file.name);
    if (allowed.length && allowed.indexOf(ext) === -1) {
      return Promise.resolve(
        'This file type (.' + (ext || "?") + ") isn't allowed here. Expected: " +
        allowed.map(function (e) { return "." + e; }).join(", ") + "."
      );
    }
    // Magic-byte check only for PDF-only fields (the pdf_file field). raw_file
    // accepts many formats, so we don't sniff it (the server's denylist does).
    if (allowed.length === 1 && allowed[0] === "pdf") {
      return readHeader(file, PDF_HEADER_BYTES).then(function (bytes) {
        if (!looksLikePdf(bytes)) {
          return "This file doesn't look like a real PDF (its contents don't " +
            "start with the PDF signature). The extension may not match the file.";
        }
        return "";
      });
    }
    return Promise.resolve("");
  }

  // --- Drop-zone rendering --------------------------------------------------

  /**
   * Paint the drop zone for the current state of its input: a "filled" card
   * (filename + size + Remove) when a file is selected, otherwise the idle
   * prompt. `error` (string) puts the zone in its error state. Also records the
   * validity on the input so the submit guard can read it.
   * @param {HTMLInputElement} input
   * @param {string} error
   */
  function renderZone(input, error) {
    var zone = input._artifactZone;
    var hasFile = input.files && input.files.length > 0;
    zone.classList.toggle("has-error", !!error);

    if (hasFile) {
      var file = input.files[0];
      var size = humanFileSize(file.size);
      zone.innerHTML =
        FILE_SVG +
        '<span class="artifact-dropzone-copy">' +
        '  <span class="artifact-dropzone-filename"></span>' +
        '  <span class="artifact-dropzone-sub"></span>' +
        '</span>' +
        '<button type="button" class="artifact-file-remove">Remove</button>';
      // textContent (not innerHTML) so a crafted filename can't inject markup.
      zone.querySelector(".artifact-dropzone-filename").textContent = file.name;
      zone.querySelector(".artifact-dropzone-sub").textContent = error
        ? error
        : (size ? size + " · drag or click to replace" : "drag or click to replace");
    } else {
      var hint = acceptHint(input);
      zone.innerHTML =
        UPLOAD_SVG +
        '<span class="artifact-dropzone-copy">' +
        '  <span class="artifact-dropzone-title">Drag &amp; drop a file here</span>' +
        '  <span class="artifact-dropzone-sub">or <span class="artifact-dropzone-link">click to browse</span>' +
        (hint ? " · " + hint : "") +
        '</span></span>';
    }
    input.setAttribute("data-artifact-invalid", error ? "true" : "false");
  }

  // --- Error summary (top of form) -----------------------------------------

  /** Remove any existing top-of-form error summary. */
  function clearSummary(form) {
    var existing = form.querySelector(".artifact-error-summary");
    if (existing) existing.parentNode.removeChild(existing);
  }

  /**
   * Render an accessible error summary at the top of the form and move focus to
   * it. `problems` is a list of {label, target} where target is the element to
   * focus/scroll to when its summary link is clicked.
   */
  function showSummary(form, problems) {
    clearSummary(form);
    var box = document.createElement("div");
    box.className = "artifact-error-summary";
    box.setAttribute("role", "alert");
    box.setAttribute("tabindex", "-1");

    var heading = document.createElement("p");
    heading.className = "artifact-error-summary-heading";
    heading.textContent =
      "Please fix the following before saving (your selected files are still attached):";
    box.appendChild(heading);

    var list = document.createElement("ul");
    problems.forEach(function (p) {
      var li = document.createElement("li");
      if (p.target && p.target.id) {
        var link = document.createElement("a");
        link.href = "#" + p.target.id;
        link.textContent = p.label;
        link.addEventListener("click", function (e) {
          e.preventDefault();
          (p.scrollTo || p.target).scrollIntoView({ behavior: "smooth", block: "center" });
          p.target.focus();
        });
        li.appendChild(link);
      } else {
        li.textContent = p.label;
      }
      list.appendChild(li);
    });
    box.appendChild(list);

    form.insertBefore(box, form.firstChild);
    box.focus();
    box.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // --- Wiring --------------------------------------------------------------

  /**
   * Turn one native file input into a standard drag-and-drop upload zone.
   * The native input is hidden (but kept focusable + submittable); the zone
   * becomes the visible control. See the file header for the a11y model.
   * @param {HTMLInputElement} input
   */
  function enhanceFileInput(input) {
    input.classList.add("artifact-file-input-hidden");

    var zone = document.createElement("div");
    zone.className = "artifact-dropzone";
    zone.setAttribute("aria-hidden", "true");
    input._artifactZone = zone;
    input.parentNode.insertBefore(zone, input.nextSibling);

    // One click handler: the Remove button clears the file; anywhere else in the
    // zone opens the native picker.
    zone.addEventListener("click", function (e) {
      if (e.target.closest(".artifact-file-remove")) {
        e.preventDefault();
        input.files = new DataTransfer().files; // clear selection
        input.dispatchEvent(new Event("change", { bubbles: true }));
        input.focus();
        return;
      }
      input.click();
    });

    ["dragenter", "dragover"].forEach(function (evt) {
      zone.addEventListener(evt, function (e) {
        e.preventDefault();
        e.stopPropagation();
        zone.classList.add("artifact-dropzone-active");
      });
    });
    ["dragleave", "dragend"].forEach(function (evt) {
      zone.addEventListener(evt, function () {
        zone.classList.remove("artifact-dropzone-active");
      });
    });
    zone.addEventListener("drop", function (e) {
      e.preventDefault();
      e.stopPropagation();
      zone.classList.remove("artifact-dropzone-active");
      if (!e.dataTransfer || !e.dataTransfer.files.length) return;
      // Assign the dropped file to the real input via DataTransfer, then fire a
      // change event so the normal validation/render path runs.
      var dt = new DataTransfer();
      dt.items.add(e.dataTransfer.files[0]);
      input.files = dt.files;
      input.dispatchEvent(new Event("change", { bubbles: true }));
    });

    // Mirror the (visually hidden) input's focus onto the zone so keyboard users
    // see a focus ring on the visible control.
    input.addEventListener("focus", function () { zone.classList.add("is-focused"); });
    input.addEventListener("blur", function () { zone.classList.remove("is-focused"); });

    // validateFile resolves asynchronously (it may read the file's header). If the
    // user picks a second file before the first finished validating, the stale
    // result must not clobber the newer one, so each change carries a token and we
    // only render the latest.
    var changeSeq = 0;
    input.addEventListener("change", function () {
      var token = ++changeSeq;
      validateFile(input).then(function (error) {
        if (token === changeSeq) renderZone(input, error || "");
      });
    });

    renderZone(input, ""); // initial paint (idle prompt)
  }

  /**
   * Submit handler: block the POST (which would lose files) when a required field
   * is empty or a selected file already failed its change-time check.
   * @param {HTMLFormElement} form
   * @param {Event} e
   */
  function onSubmit(form, e) {
    var problems = [];

    form.querySelectorAll("[required]").forEach(function (el) {
      if (el.disabled || el.type === "hidden") return;
      if (isEmpty(el)) {
        var problem = { label: labelFor(el) + " is required.", target: el };
        // For a missing required file, flag its zone and scroll to it (the input
        // itself is visually hidden).
        if (el.type === "file" && el._artifactZone) {
          el._artifactZone.classList.add("has-error");
          problem.scrollTo = el._artifactZone;
        }
        problems.push(problem);
      }
    });

    form.querySelectorAll('input[type="file"]').forEach(function (input) {
      if (input.getAttribute("data-artifact-invalid") === "true") {
        problems.push({
          label: labelFor(input) + ": please choose a valid file.",
          target: input,
          scrollTo: input._artifactZone || input,
        });
      }
    });

    if (problems.length) {
      e.preventDefault();
      showSummary(form, problems);
    }
  }

  function init() {
    var form = getArtifactForm();
    if (!form) return;
    clearSummary(form);
    form.querySelectorAll('input[type="file"]').forEach(enhanceFileInput);
    form.addEventListener("submit", function (e) { onSubmit(form, e); });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
