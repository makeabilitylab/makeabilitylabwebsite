/**
 * BioExpand — collapses an over-long member bio behind a "Show more" toggle
 * (issue #1110).
 *
 * A bio that fits in a few lines is left completely alone. Only when the text
 * exceeds COLLAPSED_LINES (~3 lines) do we clamp it with a max-height + bottom
 * fade and insert an accessible toggle button. The measurement is done in JS
 * (rather than a pure CSS line-clamp) so the clamp height tracks the element's
 * actual computed line-height and so we only add the button when it's needed.
 *
 * Accessibility: the toggle is a real <button> with aria-expanded and
 * aria-controls; focus stays on it across toggles. Animation is handled in CSS
 * and disabled under prefers-reduced-motion.
 *
 * @author Makeability Lab
 */
const BioExpand = (function () {
  'use strict';

  const COLLAPSED_LINES = 3;
  // Slack (px) so a bio that's a hair over three lines isn't needlessly clamped.
  const TOLERANCE = 4;

  let idCounter = 0;

  /** Resolve the element's line-height to a pixel value, even when computed
   *  style reports the keyword "normal". */
  function lineHeightPx(el) {
    const cs = window.getComputedStyle(el);
    const lh = parseFloat(cs.lineHeight);
    if (!isNaN(lh)) {
      return lh;
    }
    const fontSize = parseFloat(cs.fontSize) || 16;
    return fontSize * 1.5; // reasonable stand-in for "normal"
  }

  function makeCollapsible(el) {
    const collapsedMax = lineHeightPx(el) * COLLAPSED_LINES;

    // Already short enough — leave the bio as-is.
    if (el.scrollHeight <= collapsedMax + TOLERANCE) {
      return false;
    }

    if (!el.id) {
      idCounter += 1;
      el.id = 'bio-collapsible-' + idCounter;
    }

    el.classList.add('is-collapsible', 'is-collapsed');
    el.style.maxHeight = collapsedMax + 'px';

    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'bio-toggle';
    button.setAttribute('aria-expanded', 'false');
    button.setAttribute('aria-controls', el.id);
    button.textContent = 'Show more';
    // Place the toggle directly after the bio text (before the "last updated"
    // meta line, which follows in the markup).
    el.insertAdjacentElement('afterend', button);

    button.addEventListener('click', function () {
      const expanded = button.getAttribute('aria-expanded') === 'true';
      if (expanded) {
        collapse(el, button, collapsedMax);
      } else {
        expand(el, button);
      }
    });

    return true;
  }

  function prefersReducedMotion() {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  function expand(el, button) {
    el.classList.remove('is-collapsed');
    button.setAttribute('aria-expanded', 'true');
    button.textContent = 'Show less';

    if (prefersReducedMotion()) {
      el.style.maxHeight = 'none';
      return;
    }

    // Animate from the clamped height to the full content height, then drop the
    // explicit max-height so the bio can reflow (e.g. on resize). We must NOT
    // clear it early or mid-transition — "none" isn't animatable and would jump
    // the bio open — so we wait for transitionend, and we re-check aria-expanded
    // in case the user collapsed again before the animation finished (avoids a
    // stale handler forcing the bio back open).
    el.style.maxHeight = el.scrollHeight + 'px';
    const onEnd = function (event) {
      if (event.target !== el || event.propertyName !== 'max-height') {
        return;
      }
      el.removeEventListener('transitionend', onEnd);
      if (button.getAttribute('aria-expanded') === 'true') {
        el.style.maxHeight = 'none';
      }
    };
    el.addEventListener('transitionend', onEnd);
  }

  function collapse(el, button, collapsedMax) {
    button.setAttribute('aria-expanded', 'false');
    button.textContent = 'Show more';

    if (prefersReducedMotion()) {
      el.classList.add('is-collapsed');
      el.style.maxHeight = collapsedMax + 'px';
      return;
    }

    // Can't transition from "none" (or ""), so pin an explicit start height and
    // force a reflow, then animate down to the clamped height on the next frame.
    if (el.style.maxHeight === 'none' || el.style.maxHeight === '') {
      el.style.maxHeight = el.scrollHeight + 'px';
      void el.offsetHeight; // reflow so the browser registers the start height
    }
    el.classList.add('is-collapsed');
    window.requestAnimationFrame(function () {
      el.style.maxHeight = collapsedMax + 'px';
    });
  }

  /**
   * @param {string} selector - elements to evaluate (e.g. '[data-bio-collapsible]')
   */
  function init(selector) {
    const process = function () {
      const elements = document.querySelectorAll(selector);
      Array.prototype.forEach.call(elements, function (el) {
        if (el.dataset.bioProcessed) {
          return;
        }
        // Mark processed only once we've actually clamped it; otherwise leave it
        // unmarked so the window 'load' pass can re-check (late-loading images
        // or fonts can push a short-looking bio over the threshold).
        if (makeCollapsible(el)) {
          el.dataset.bioProcessed = 'true';
        }
      });
    };

    process();
    // Re-measure after everything (fonts/images) has loaded and may have
    // changed the bio's height.
    window.addEventListener('load', process);
  }

  return { init: init };
})();
