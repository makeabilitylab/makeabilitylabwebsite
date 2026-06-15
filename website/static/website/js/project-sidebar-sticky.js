/**
 * project-sidebar-sticky.js
 *
 * Hybrid sticky-offset for the project page right sidebar (#1245).
 *
 * Plain CSS can't express "stick at top:--project-sidebar-top-offset for short
 * sidebars, anchor at bottom for tall ones" because CSS sticky percentage
 * offsets refer to the containing block (the flex parent) — not the sticky
 * element's own height. This script measures the sidebar's rendered height
 * and sets the --sidebar-sticky-top custom property so the CSS picks the
 * right offset.
 *
 * Behavior:
 *   - Short sidebar (fits in viewport minus header+gap): --sidebar-sticky-top
 *     is set to --project-sidebar-top-offset. Sidebar sticks at the top while
 *     the user scrolls the main column.
 *   - Tall sidebar: --sidebar-sticky-top is a negative px value
 *     (viewport - height - bottom-gap). Sidebar scrolls naturally with the
 *     page until its bottom reaches (viewport_bottom - bottom-gap), then
 *     pins there. Main content keeps scrolling past.
 *
 * Single source of truth:
 *   - Breakpoint: `window.matchMedia('(min-width: 992px)')` — same query as
 *     the @media rule in project.css. No duplicated 992 constant.
 *   - Layout values: read --project-sidebar-top-offset and
 *     --project-sidebar-bottom-gap from the sidebar's computed style. No
 *     duplicated 100 or 20 constants.
 *
 * Re-runs:
 *   - DOMContentLoaded — initial sizing
 *   - window.load — re-measure after lead avatar images finish loading (the
 *     production case where DCL-time measurement is too early)
 *   - resize — adapt when the user resizes the browser
 *   - ResizeObserver on the sidebar — catch any other layout shift
 *     (collapsible sections, font swaps, etc.)
 *
 * Only active on >=992px breakpoint; the mobile layout doesn't use sticky.
 *
 * Vanilla JS — no jQuery dependency.
 */
(function () {
  'use strict';

  // Mirrors the @media query in project.css; if that breakpoint moves, this
  // moves with it automatically.
  var desktopMQ = window.matchMedia('(min-width: 992px)');

  function readPxVar(element, varName, fallback) {
    var raw = getComputedStyle(element).getPropertyValue(varName).trim();
    var parsed = parseFloat(raw);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  function updateStickyTop() {
    var sidebar = document.querySelector('.project-sidebar');
    if (!sidebar) return;

    // On mobile (<992px) the sidebar isn't sticky; clear any prior override.
    if (!desktopMQ.matches) {
      sidebar.style.removeProperty('--sidebar-sticky-top');
      return;
    }

    // Read layout constants from CSS — single source of truth.
    var topOffset = readPxVar(sidebar, '--project-sidebar-top-offset', 100);
    var bottomGap = readPxVar(sidebar, '--project-sidebar-bottom-gap', 20);

    var sidebarHeight = sidebar.offsetHeight;
    var viewportHeight = window.innerHeight;
    var availableHeight = viewportHeight - topOffset - bottomGap;

    var topValue;
    if (sidebarHeight > availableHeight) {
      // Tall: anchor by the sidebar's bottom with `bottomGap` of breathing room.
      topValue = (viewportHeight - sidebarHeight - bottomGap) + 'px';
    } else {
      // Short: sticky-top, leaves room for the page header.
      topValue = topOffset + 'px';
    }
    sidebar.style.setProperty('--sidebar-sticky-top', topValue);
  }

  // Debounce resize so we don't recalc on every pixel of a slow drag.
  var resizeTimer = null;
  function onResize() {
    if (resizeTimer) clearTimeout(resizeTimer);
    resizeTimer = setTimeout(updateStickyTop, 75);
  }

  // Initial measurement when the DOM is parsed…
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', updateStickyTop);
  } else {
    updateStickyTop();
  }
  // …and re-measure after images finish loading (lead avatars in prod can
  // grow the sidebar by hundreds of pixels after DCL).
  window.addEventListener('load', updateStickyTop);
  window.addEventListener('resize', onResize);

  // Catch any other layout shift (collapsible sections, font swaps, etc.).
  if (typeof ResizeObserver !== 'undefined') {
    var observer = new ResizeObserver(updateStickyTop);
    function attachObserver() {
      var sidebar = document.querySelector('.project-sidebar');
      if (sidebar) observer.observe(sidebar);
    }
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', attachObserver);
    } else {
      attachObserver();
    }
  }
})();
