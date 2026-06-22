/**
 * ============================================================================
 * ARTIFACT PREVIEW POPOVER MODULE
 * ============================================================================
 *
 * Opens a small card previewing a publication's poster / talk-slides thumbnail
 * plus download actions (PDF, the raw file e.g. PPTX, and the editable Source
 * link). Implements issue #840.
 *
 * The trigger is the "Poster" / "Talk" link rendered by
 * snippets/artifact_preview_link.html. Behavior mirrors the Cite popover
 * (citationPopoverSimple.js):
 *
 *   - MOUSE: hovering the trigger opens the card (a passive glance that
 *     auto-closes when the pointer leaves). Clicking PINS it open so the user
 *     can interact without holding hover.
 *   - KEYBOARD: Enter/Space activates the trigger (a click), which opens and
 *     pins the card and moves focus to its first action. Focus is kept within
 *     the card while pinned; Escape closes it and restores focus to the trigger.
 *   - TOUCH: there is no hover, so a tap just opens (pins) the card — the same
 *     accessible path as keyboard.
 *
 * The trigger keeps `href` pointing at the PDF, so with JS disabled it still
 * works as a plain download link (progressive enhancement).
 *
 * The card's HTML lives in a per-trigger <template>, which is inert until we
 * clone it into the DOM on open — so the preview <img> is only fetched when the
 * card is shown (lazy), even on a page listing dozens of publications.
 *
 * DEPENDENCIES:
 *   - None (self-contained vanilla JS). Builds a Bootstrap-3-styled `.popover`
 *     so the site's existing popover CSS (border, shadow, arrow) applies;
 *     `.artifact-preview-*` in publications.css styles the card contents.
 *
 * DESIGN:
 *   Self-initializing and fully event-delegated, so triggers injected after
 *   load (the member page's AJAX "load more", #1110) work with no re-init.
 *
 * @version 2.0.0
 * @author Makeability Lab
 * ============================================================================
 */
(function () {
  'use strict';

  /* ===========================================================================
     CONSTANTS
     =========================================================================== */

  const TRIGGER_SEL = '.artifact-preview-trigger';
  const FOCUSABLE_SEL =
    'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])';

  /** Gap (px) between the trigger and the card (matches Bootstrap's popover). */
  const GAP = 10;
  /** Viewport padding (px) used when clamping the card on screen. */
  const PAD = 8;
  /** Half the popover arrow's box size (Bootstrap's `.arrow` border-width is 11px). */
  const ARROW_HALF = 11;
  /** Delay (ms) before a hover-opened card hides, so the pointer can reach it. */
  const HIDE_DELAY = 140;

  /* ===========================================================================
     STATE
     ===========================================================================
     Only one card is open at a time. `pinned` is true when it was opened by
     click/Enter/tap (stays open until Escape / outside-click / re-click) versus
     hover (auto-closes on mouse-leave). */

  let activeTrigger = null;
  let activePopover = null;
  let pinned = false;
  let hideTimer = null;

  /* ===========================================================================
     HELPERS
     =========================================================================== */

  /** True only on devices with a real hovering pointer (excludes touch). */
  function canHover() {
    return window.matchMedia && window.matchMedia('(hover: hover)').matches;
  }

  function cancelHide() {
    if (hideTimer) {
      clearTimeout(hideTimer);
      hideTimer = null;
    }
  }

  /** The <template> holding a trigger's card markup. */
  function getTemplate(trigger) {
    const wrapper = trigger.closest('.artifact-preview');
    return wrapper
      ? wrapper.querySelector('template.artifact-preview-template')
      : null;
  }

  function getFocusables(root) {
    return Array.prototype.slice.call(root.querySelectorAll(FOCUSABLE_SEL));
  }

  /**
   * Builds the card popover for a trigger by cloning its <template> into
   * Bootstrap-3 popover markup (so the existing `.popover` CSS applies). The
   * clone is what makes the preview image load — the <template> was inert.
   *
   * @param {HTMLElement} trigger - The trigger link
   * @returns {HTMLElement|null} The `.popover` element, or null if no template
   */
  function buildPopover(trigger) {
    const template = getTemplate(trigger);
    if (!template) {
      return null;
    }

    const popover = document.createElement('div');
    popover.className = 'popover artifact-preview-popover';

    const arrow = document.createElement('div');
    arrow.className = 'arrow';
    popover.appendChild(arrow);

    const content = document.createElement('div');
    content.className = 'popover-content';
    content.appendChild(template.content.cloneNode(true));
    popover.appendChild(content);

    return popover;
  }

  /**
   * Positions a rendered card relative to its trigger using Bootstrap's "auto
   * right" rule: prefer the right side, flip to the left when there isn't room.
   * Vertically centers on the trigger, clamps to the viewport, and moves the
   * arrow to keep pointing at the trigger. (Same math as citationPopoverSimple.js.)
   *
   * @param {HTMLElement} trigger - The trigger link
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

    const placement =
      rect.right + GAP + width > viewportWidth ? 'left' : 'right';
    popover.classList.remove('left', 'right');
    popover.classList.add(placement);

    const left = placement === 'right'
      ? rect.right + scrollX
      : rect.left + scrollX - width;

    const desiredTop = rect.top + scrollY + rect.height / 2 - height / 2;
    const minTop = scrollY + PAD;
    const maxTop = scrollY + viewportHeight - height - PAD;
    const top = Math.max(minTop, Math.min(desiredTop, Math.max(minTop, maxTop)));

    popover.style.left = left + 'px';
    popover.style.top = top + 'px';

    const arrow = popover.querySelector('.arrow');
    if (arrow) {
      const triggerCenterY = rect.top + scrollY + rect.height / 2;
      const arrowCenter = Math.max(
        ARROW_HALF + PAD,
        Math.min(triggerCenterY - top, height - ARROW_HALF - PAD)
      );
      arrow.style.top = (arrowCenter - ARROW_HALF) + 'px';
      arrow.style.marginTop = '0';
    }
  }

  /* ===========================================================================
     OPEN / CLOSE
     =========================================================================== */

  function removeActive() {
    if (activePopover) {
      activePopover.remove();
    }
    if (activeTrigger) {
      activeTrigger.setAttribute('aria-expanded', 'false');
    }
    activePopover = null;
    activeTrigger = null;
    pinned = false;
  }

  /**
   * Opens the card for a trigger.
   *
   * @param {HTMLElement} trigger - The trigger link
   * @param {boolean} pin - Pin it open (click/keyboard/touch) vs. hover-open
   */
  function open(trigger, pin) {
    cancelHide();

    // Already open for this trigger: just upgrade hover-open to pinned, and
    // move focus in if we are pinning now.
    if (activeTrigger === trigger && activePopover) {
      if (pin && !pinned) {
        pinned = true;
        focusFirst(activePopover);
      }
      return;
    }

    removeActive();

    const popover = buildPopover(trigger);
    if (!popover) {
      return;
    }
    // Render hidden first so we can measure it, then position and reveal.
    popover.style.display = 'block';
    popover.style.visibility = 'hidden';
    document.body.appendChild(popover);

    activeTrigger = trigger;
    activePopover = popover;
    pinned = !!pin;

    positionPopover(trigger, popover);
    popover.style.visibility = 'visible';
    trigger.setAttribute('aria-expanded', 'true');

    if (pin) {
      focusFirst(popover);
    }
  }

  function focusFirst(popover) {
    const focusables = getFocusables(popover);
    if (focusables.length) {
      focusables[0].focus();
    }
  }

  /**
   * Closes the open card.
   *
   * @param {boolean} returnFocus - Restore focus to the trigger (for keyboard)
   */
  function close(returnFocus) {
    const trigger = activeTrigger;
    removeActive();
    cancelHide();
    if (returnFocus && trigger) {
      trigger.focus();
    }
  }

  function scheduleHide() {
    if (pinned) {
      return;
    }
    cancelHide();
    hideTimer = setTimeout(function () {
      close(false);
    }, HIDE_DELAY);
  }

  /* ===========================================================================
     EVENT HANDLERS (delegated on document)
     =========================================================================== */

  function onMouseOver(event) {
    if (!canHover()) {
      return;
    }
    const trigger = event.target.closest(TRIGGER_SEL);
    if (trigger) {
      cancelHide();
      if (activeTrigger !== trigger) {
        open(trigger, false);
      }
      return;
    }
    // Pointer moved onto the open card: keep it open (hoverable).
    if (activePopover && activePopover.contains(event.target)) {
      cancelHide();
    }
  }

  function onMouseOut(event) {
    if (!canHover() || pinned || (!activeTrigger && !activePopover)) {
      return;
    }
    const to = event.relatedTarget;
    const stillOnTrigger = activeTrigger && to && activeTrigger.contains(to);
    const stillOnPopover = activePopover && to && activePopover.contains(to);
    if (!stillOnTrigger && !stillOnPopover) {
      scheduleHide();
    }
  }

  function onClick(event) {
    const trigger = event.target.closest(TRIGGER_SEL);
    if (trigger) {
      // Open the card instead of navigating to the PDF (that's available as an
      // action inside the card). Re-clicking a pinned card closes it.
      event.preventDefault();
      if (activeTrigger === trigger && pinned) {
        close(false);
      } else {
        open(trigger, true);
      }
      return;
    }
    // A click anywhere outside a pinned card closes it. (Action links inside
    // the card are not triggers and fall through here to navigate normally.)
    if (pinned && activePopover && !activePopover.contains(event.target)) {
      close(false);
    }
  }

  function onKeyDown(event) {
    if (!activePopover) {
      return;
    }
    if (event.key === 'Escape') {
      event.preventDefault();
      close(true);
      return;
    }
    // While pinned, keep Tab focus cycling within the card so keyboard users
    // can reach every action and can't tab off into the page behind it.
    if (event.key === 'Tab' && pinned) {
      const focusables = getFocusables(activePopover);
      if (!focusables.length) {
        return;
      }
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  }

  function reposition() {
    if (activeTrigger && activePopover) {
      positionPopover(activeTrigger, activePopover);
    }
  }

  /* ===========================================================================
     INIT
     =========================================================================== */

  function init() {
    if (init._done) {
      return;
    }
    init._done = true;

    document.addEventListener('mouseover', onMouseOver);
    document.addEventListener('mouseout', onMouseOut);
    document.addEventListener('click', onClick);
    document.addEventListener('keydown', onKeyDown);
    window.addEventListener('resize', reposition);
    window.addEventListener('scroll', reposition, { passive: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
