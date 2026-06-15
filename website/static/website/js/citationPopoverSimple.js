/**
 * ============================================================================
 * CITATION POPOVER MODULE
 * ============================================================================
 *
 * Handles citation popover functionality for publication links. Provides
 * copy-to-clipboard and download functionality for both plain text citations
 * and BibTeX format.
 *
 * USAGE:
 *   // Initialize on page load
 *   document.addEventListener('DOMContentLoaded', function() {
 *     CitationPopover.init('.publication-citation-link');
 *   });
 *
 * DEPENDENCIES:
 *   - None. This is self-contained vanilla JS (no jQuery, no Bootstrap JS).
 *     It builds a Bootstrap-3-styled popover (.popover / .popover-title /
 *     .popover-content / .arrow markup) so the existing Bootstrap + custom
 *     popover CSS still applies. See issues #1288 / #1253 (Track A) for the
 *     jQuery / Bootstrap-JS removal this is part of.
 *
 * BEHAVIOR (matches the previous Bootstrap-popover version):
 *   - Trigger uses `title` + `data-content` (HTML) on the link.
 *   - Placement is "auto right": the popover sits to the right of the trigger,
 *     flipping to the left when there isn't room. It is vertically centered on
 *     the trigger and clamped to the viewport, with the arrow tracking the
 *     trigger. Only one popover is open at a time.
 *   - Content is rebuilt from `data-content` on each open, so the format
 *     toggle always starts on "Text" (same as the Bootstrap version).
 *
 * ACCESSIBILITY:
 *   - Manages aria-expanded state on trigger elements
 *   - Manages aria-pressed state on format toggle buttons
 *   - Provides visual feedback for copy operations
 *
 * @version 4.0.0 - Replaced Bootstrap 3 popover (jQuery) with vanilla JS
 * @author Makeability Lab
 * ============================================================================
 */
const CitationPopover = (function () {
  'use strict';

  /* ===========================================================================
     CONSTANTS
     =========================================================================== */

  /** Duration (ms) to show the "Copied!" feedback */
  const COPY_FEEDBACK_DURATION = 1500;

  /** Gap (px) between the trigger and the popover — matches Bootstrap's
   *  `.popover.right { margin-left: 10px }` / `.popover.left { margin-left: -10px }`. */
  const POPOVER_GAP = 10;

  /** Half the popover arrow's box size (Bootstrap's `.arrow` border-width is 11px). */
  const ARROW_HALF = 11;

  /** Viewport padding (px) used when clamping the popover on screen. */
  const VIEWPORT_PADDING = 8;

  /** CSS selectors used throughout the module */
  const SELECTORS = {
    popoverTrigger: '[data-toggle="popover"]',
    popover: '.popover',
    citationText: '.citation-text',
    bibtexText: '.bibtex-text',
    formatBtn: '.citation-format-btn',
    copyBtn: '.citation-copy',
    downloadBtn: '.citation-download'
  };

  /* ===========================================================================
     POPOVER STATE
     ===========================================================================
     Only one citation popover is open at a time. `activeTrigger` is the trigger
     whose popover is currently shown (null if none); `activePopover` is its
     `.popover` element (appended to <body>). */

  let activeTrigger = null;
  let activePopover = null;


  /* ===========================================================================
     PRIVATE FUNCTIONS
     =========================================================================== */

  /**
   * Gets the currently visible citation text (plain text or BibTeX).
   *
   * @returns {string|null} The citation text, or null if not found
   */
  function getVisibleCitationText() {
    const citationEl = document.querySelector(SELECTORS.citationText);
    const bibtexEl = document.querySelector(SELECTORS.bibtexText);

    if (!citationEl || !bibtexEl) {
      console.warn('Citation elements not found in popover');
      return null;
    }

    // Return whichever format is currently visible
    return citationEl.style.display !== 'none'
      ? citationEl.textContent.trim()
      : bibtexEl.textContent.trim();
  }

  /**
   * Checks if BibTeX format is currently active.
   *
   * @returns {boolean} True if BibTeX is the active format
   */
  function isBibtexActive() {
    const bibtexEl = document.querySelector(SELECTORS.bibtexText);
    return bibtexEl && bibtexEl.style.display !== 'none';
  }

  /**
   * Updates aria-expanded attribute on a trigger element.
   *
   * @param {HTMLElement} trigger - The popover trigger element
   * @param {boolean} isExpanded - Whether the popover is expanded
   */
  function setAriaExpanded(trigger, isExpanded) {
    trigger.setAttribute('aria-expanded', String(isExpanded));
  }

  /**
   * Updates aria-pressed attributes on format toggle buttons.
   *
   * @param {string} activeFormat - The active format ('text' or 'bibtex')
   */
  function setAriaPressed(activeFormat) {
    document.querySelectorAll(SELECTORS.formatBtn).forEach(btn => {
      const btnFormat = btn.dataset.format;
      btn.setAttribute('aria-pressed', String(btnFormat === activeFormat));
    });
  }

  /**
   * Shows temporary feedback (e.g., "Copied!") near an element.
   *
   * @param {HTMLElement} element - Element to append feedback to
   * @param {string} message - Message to display
   */
  function showFeedback(element, message) {
    // Remove any existing feedback
    document.querySelectorAll('.citation-copied-feedback').forEach(el => el.remove());

    const feedback = document.createElement('span');
    feedback.className = 'citation-copied-feedback';
    feedback.textContent = message;
    element.appendChild(feedback);

    setTimeout(() => {
      feedback.style.opacity = '0';
      feedback.style.transition = 'opacity 0.2s';
      setTimeout(() => feedback.remove(), 200);
    }, COPY_FEEDBACK_DURATION);
  }


  /* ===========================================================================
     POPOVER SHOW / HIDE / POSITION
     =========================================================================== */

  /**
   * Builds the popover element for a trigger, mirroring Bootstrap 3's popover
   * markup so the existing `.popover` CSS applies. Content/title come from the
   * trigger's `data-content` and `data-original-title` (set up in `init`).
   *
   * @param {HTMLElement} trigger - The trigger element
   * @returns {HTMLElement} The `.popover` element (not yet positioned)
   */
  function buildPopover(trigger) {
    const popover = document.createElement('div');
    popover.className = 'popover';
    popover.setAttribute('role', 'tooltip');

    const arrow = document.createElement('div');
    arrow.className = 'arrow';
    popover.appendChild(arrow);

    const title = trigger.getAttribute('data-original-title') || '';
    if (title) {
      const titleEl = document.createElement('h3');
      titleEl.className = 'popover-title';
      titleEl.textContent = title;
      popover.appendChild(titleEl);
    }

    const contentEl = document.createElement('div');
    contentEl.className = 'popover-content';
    // data-content is trusted, author-authored HTML (rendered server-side from
    // the Publication), matching the previous `html: true` Bootstrap popover.
    contentEl.innerHTML = trigger.getAttribute('data-content') || '';
    popover.appendChild(contentEl);

    return popover;
  }

  /**
   * Positions an already-rendered popover relative to its trigger using
   * Bootstrap's "auto right" rule: prefer the right side, flip to the left when
   * there isn't room. Vertically centers on the trigger, clamps to the viewport,
   * and moves the arrow to keep pointing at the trigger.
   *
   * @param {HTMLElement} trigger - The trigger element
   * @param {HTMLElement} popover - The `.popover` element (already in the DOM)
   */
  function positionPopover(trigger, popover) {
    const rect = trigger.getBoundingClientRect();
    const scrollX = window.pageXOffset;
    const scrollY = window.pageYOffset;
    const viewportWidth = document.documentElement.clientWidth;
    const viewportHeight = document.documentElement.clientHeight;
    const width = popover.offsetWidth;
    const height = popover.offsetHeight;

    // "auto right": prefer right, flip to left if the popover would overflow.
    const placement =
      rect.right + POPOVER_GAP + width > viewportWidth ? 'left' : 'right';
    popover.classList.remove('left', 'right');
    popover.classList.add(placement);

    // Horizontal: the CSS margin (POPOVER_GAP) creates the visible gap, so the
    // popover edge sits flush against the trigger here.
    const left = placement === 'right'
      ? rect.right + scrollX
      : rect.left + scrollX - width;

    // Vertical: center on the trigger, then clamp within the viewport.
    const desiredTop = rect.top + scrollY + rect.height / 2 - height / 2;
    const minTop = scrollY + VIEWPORT_PADDING;
    const maxTop = scrollY + viewportHeight - height - VIEWPORT_PADDING;
    const top = Math.max(minTop, Math.min(desiredTop, Math.max(minTop, maxTop)));

    popover.style.left = left + 'px';
    popover.style.top = top + 'px';

    // Move the arrow so it still points at the trigger's vertical center even
    // after clamping. (Bootstrap does the same via an inline top + margin.)
    const arrow = popover.querySelector('.arrow');
    if (arrow) {
      const triggerCenterY = rect.top + scrollY + rect.height / 2;
      const arrowCenter = Math.max(
        ARROW_HALF + VIEWPORT_PADDING,
        Math.min(triggerCenterY - top, height - ARROW_HALF - VIEWPORT_PADDING)
      );
      arrow.style.top = (arrowCenter - ARROW_HALF) + 'px';
      arrow.style.marginTop = '0';
    }
  }

  /**
   * Shows the popover for a trigger (closing any other open popover first).
   *
   * @param {HTMLElement} trigger - The trigger element
   */
  function showPopover(trigger) {
    closeOtherPopovers(trigger);

    const popover = buildPopover(trigger);
    // Render hidden first so we can measure it, then position and reveal.
    popover.style.display = 'block';
    popover.style.visibility = 'hidden';
    document.body.appendChild(popover);

    activeTrigger = trigger;
    activePopover = popover;

    positionPopover(trigger, popover);
    popover.style.visibility = 'visible';

    setAriaExpanded(trigger, true);
  }

  /**
   * Hides the popover for a trigger, if it is the one currently open.
   *
   * @param {HTMLElement} trigger - The trigger element
   */
  function hidePopover(trigger) {
    if (activeTrigger === trigger && activePopover) {
      activePopover.remove();
      activePopover = null;
      activeTrigger = null;
    }
    setAriaExpanded(trigger, false);
  }

  /**
   * Closes any open popover except the one for the specified trigger.
   *
   * @param {HTMLElement|null} exceptTrigger - Trigger to leave open
   */
  function closeOtherPopovers(exceptTrigger) {
    if (activeTrigger && activeTrigger !== exceptTrigger) {
      hidePopover(activeTrigger);
    }
  }

  /**
   * Checks if a popover is currently visible for a trigger.
   *
   * @param {HTMLElement} trigger - The trigger element
   * @returns {boolean} True if popover is visible
   */
  function isPopoverVisible(trigger) {
    return activeTrigger === trigger && activePopover !== null;
  }


  /* ===========================================================================
     FORMAT SWITCHING
     =========================================================================== */

  /**
   * Switches to plain text citation view.
   */
  function showCitation() {
    const citationEl = document.querySelector(SELECTORS.citationText);
    const bibtexEl = document.querySelector(SELECTORS.bibtexText);

    if (citationEl) citationEl.style.display = 'block';
    if (bibtexEl) bibtexEl.style.display = 'none';

    // Update button states
    document.querySelectorAll(SELECTORS.formatBtn).forEach(btn => {
      btn.classList.toggle('active', btn.dataset.format === 'text');
    });

    setAriaPressed('text');
  }

  /**
   * Switches to BibTeX citation view.
   */
  function showBibtex() {
    const citationEl = document.querySelector(SELECTORS.citationText);
    const bibtexEl = document.querySelector(SELECTORS.bibtexText);

    if (citationEl) citationEl.style.display = 'none';
    if (bibtexEl) bibtexEl.style.display = 'block';

    // Update button states
    document.querySelectorAll(SELECTORS.formatBtn).forEach(btn => {
      btn.classList.toggle('active', btn.dataset.format === 'bibtex');
    });

    setAriaPressed('bibtex');
  }


  /* ===========================================================================
     COPY & DOWNLOAD
     =========================================================================== */

  /**
   * Copies the currently visible citation to clipboard.
   *
   * @param {HTMLElement} button - The button that triggered the copy
   */
  function copyCitation(button) {
    const citationText = getVisibleCitationText();

    if (!citationText) {
      console.error('No citation text found to copy');
      return;
    }

    if (!navigator.clipboard) {
      console.warn('Clipboard API not available');
      alert('Unable to copy. Please select and copy the text manually.');
      return;
    }

    navigator.clipboard.writeText(citationText)
      .then(() => showFeedback(button, 'Copied!'))
      .catch(err => {
        console.error('Failed to copy citation:', err);
        alert('Failed to copy. Please select and copy the text manually.');
      });
  }

  /**
   * Downloads the currently visible citation as a file.
   *
   * @param {string} filenameBase - Base filename without extension
   */
  function downloadCitation(filenameBase) {
    const citationText = getVisibleCitationText();

    if (!citationText) {
      console.error('No citation text found to download');
      return;
    }

    const extension = isBibtexActive() ? '.bib' : '.txt';
    const filename = filenameBase + '-Citation' + extension;

    const blob = new Blob([citationText], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.style.display = 'none';
    document.body.appendChild(link);
    link.click();

    // Cleanup
    setTimeout(() => {
      URL.revokeObjectURL(url);
      link.remove();
    }, 100);
  }


  /* ===========================================================================
     EVENT HANDLERS
     =========================================================================== */

  /**
   * Handles clicks on format toggle buttons.
   *
   * @param {Event} event - The click event
   */
  function handleFormatClick(event) {
    const btn = event.target.closest(SELECTORS.formatBtn);
    if (!btn) return;

    if (btn.dataset.format === 'bibtex') {
      showBibtex();
    } else {
      showCitation();
    }
  }

  /**
   * Handles clicks on the copy button.
   *
   * @param {Event} event - The click event
   */
  function handleCopyClick(event) {
    const btn = event.target.closest(SELECTORS.copyBtn);
    if (!btn) return;

    copyCitation(btn);
  }

  /**
   * Handles clicks on the download button.
   *
   * @param {Event} event - The click event
   */
  function handleDownloadClick(event) {
    const btn = event.target.closest(SELECTORS.downloadBtn);
    if (!btn) return;

    const filename = btn.dataset.filename;
    if (filename) {
      downloadCitation(filename);
    }
  }

  /**
   * Handles clicks outside the open popover to close it.
   *
   * @param {Event} event - The click event
   */
  function handleOutsideClick(event) {
    if (!activeTrigger || !activePopover) {
      return;
    }

    const target = event.target;
    const isClickOnTrigger = activeTrigger.contains(target);
    const isClickInPopover = activePopover.contains(target);

    if (!isClickOnTrigger && !isClickInPopover) {
      hidePopover(activeTrigger);
    }
  }

  /**
   * Handles click on a popover trigger.
   *
   * @param {Event} event - The click event
   * @param {HTMLElement} trigger - The trigger element
   */
  function handleTriggerClick(event, trigger) {
    event.preventDefault();

    if (isPopoverVisible(trigger)) {
      hidePopover(trigger);
    } else {
      showPopover(trigger);
    }
  }


  /* ===========================================================================
     PUBLIC API
     =========================================================================== */

  /**
   * Initializes citation popover functionality.
   *
   * @param {string} selector - CSS selector for citation link elements
   *
   * @example
   * CitationPopover.init('.publication-citation-link');
   */
  function init(selector) {
    const triggers = document.querySelectorAll(selector);

    if (triggers.length === 0) {
      return;
    }

    triggers.forEach(trigger => {
      // Stash the title in data-original-title and remove the title attribute so
      // the browser's native tooltip doesn't show on hover. (Bootstrap did this
      // for us before; we now do it explicitly.)
      if (trigger.hasAttribute('title')) {
        trigger.setAttribute('data-original-title', trigger.getAttribute('title'));
        trigger.removeAttribute('title');
      }

      trigger.addEventListener('click', event => handleTriggerClick(event, trigger));
    });

    // Close the open popover when clicking outside of it.
    document.addEventListener('click', handleOutsideClick);

    // Close the open popover on Escape (a11y) and restore focus to its trigger.
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && activeTrigger) {
        const trigger = activeTrigger;
        hidePopover(trigger);
        trigger.focus();
      }
    });

    // Event delegation for popover content (it is created dynamically on open).
    document.addEventListener('click', event => {
      handleFormatClick(event);
      handleCopyClick(event);
      handleDownloadClick(event);
    });

    // Keep the open popover anchored to its trigger when the page reflows.
    window.addEventListener('resize', () => {
      if (activeTrigger && activePopover) {
        positionPopover(activeTrigger, activePopover);
      }
    });
  }

  // Expose public API
  return {
    init
  };

})();
