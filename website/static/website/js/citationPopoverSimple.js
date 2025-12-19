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
 *   - Bootstrap 3 Popover (requires jQuery for popover API only)
 * 
 * ACCESSIBILITY:
 *   - Manages aria-expanded state on trigger elements
 *   - Manages aria-pressed state on format toggle buttons
 *   - Provides visual feedback for copy operations
 * 
 * @version 3.0.0
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

  /**
   * Closes all open popovers except the specified one.
   * 
   * @param {HTMLElement|null} exceptTrigger - Trigger to exclude from closing
   */
  function closeOtherPopovers(exceptTrigger) {
    document.querySelectorAll(SELECTORS.popoverTrigger).forEach(trigger => {
      if (trigger !== exceptTrigger) {
        // Bootstrap 3 popover API requires jQuery
        $(trigger).popover('hide');
        setAriaExpanded(trigger, false);
      }
    });
  }

  /**
   * Checks if a popover is currently visible for a trigger.
   * 
   * @param {HTMLElement} trigger - The trigger element
   * @returns {boolean} True if popover is visible
   */
  function isPopoverVisible(trigger) {
    const popover = trigger.nextElementSibling;
    return popover && popover.classList.contains('popover') &&
      popover.style.display !== 'none';
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
   * Handles clicks outside popovers to close them.
   * 
   * @param {Event} event - The click event
   * @param {NodeList} triggers - The popover trigger elements
   */
  function handleOutsideClick(event, triggers) {
    const target = event.target;

    triggers.forEach(trigger => {
      const isClickOnTrigger = trigger.contains(target);
      const popover = document.querySelector(SELECTORS.popover);
      const isClickInPopover = popover && popover.contains(target);

      if (!isClickOnTrigger && !isClickInPopover) {
        $(trigger).popover('hide');
        setAriaExpanded(trigger, false);
      }
    });
  }

  /**
   * Handles click on a popover trigger.
   * 
   * @param {Event} event - The click event
   * @param {HTMLElement} trigger - The trigger element
   */
  function handleTriggerClick(event, trigger) {
    event.preventDefault();

    // Close other popovers first
    closeOtherPopovers(trigger);

    // Toggle this popover (Bootstrap 3 API)
    $(trigger).popover('toggle');

    // Update aria-expanded after Bootstrap finishes
    setTimeout(() => {
      setAriaExpanded(trigger, isPopoverVisible(trigger));
    }, 10);
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

    // Initialize Bootstrap popovers and click handlers on each trigger
    triggers.forEach(trigger => {
      // Initialize Bootstrap popover (requires jQuery)
      $(trigger).popover({
        placement: 'auto right',
        trigger: 'manual',
        html: true
      });

      // Handle trigger clicks
      trigger.addEventListener('click', event => handleTriggerClick(event, trigger));
    });

    // Global click handler for closing popovers when clicking outside
    document.addEventListener('click', event => handleOutsideClick(event, triggers));

    // Event delegation for popover content (since it's dynamically created)
    document.addEventListener('click', event => {
      handleFormatClick(event);
      handleCopyClick(event);
      handleDownloadClick(event);
    });
  }

  // Expose public API
  return {
    init
  };

})();