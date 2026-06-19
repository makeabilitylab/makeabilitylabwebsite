/*!
 * Shared reduced-motion helper.
 *
 * A single place for the `prefers-reduced-motion: reduce` check so every motion
 * source on the site agrees. Exposed as a global (a classic script, not an ES
 * module) so it can be consulted by both classic scripts (e.g. carousel.js) and
 * ES modules (e.g. makelab-logo.js) alike.
 *
 * Load this BEFORE any script that needs it (see base.html). It queries
 * matchMedia LIVE on each call, so toggling the OS setting mid-session is
 * respected without a reload.
 *
 * Usage:
 *   if (window.MakeLab.prefersReducedMotion()) { ...skip/stop animation... }
 *
 * See issue #1294. Candidates to migrate onto this helper (currently each ships
 * its own copy): project-listing-filter.js, bio-expand.js, member-nav.js.
 */
(function () {
  'use strict';

  window.MakeLab = window.MakeLab || {};

  /**
   * @returns {boolean} true if the user has requested reduced motion at the OS
   *   level. Falls back to false when matchMedia is unavailable.
   */
  window.MakeLab.prefersReducedMotion = function prefersReducedMotion() {
    return !!(
      window.matchMedia &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    );
  };
})();
