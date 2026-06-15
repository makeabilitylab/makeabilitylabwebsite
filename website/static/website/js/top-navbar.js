/*!
 * Top navbar behavior — vanilla JS, no jQuery.
 *
 * Drives the responsive (mobile) navbar collapse, replacing Bootstrap 3's
 * collapse data-api as part of the jQuery / Bootstrap-JS removal
 * (Track A, see issues #1288 / #1253). The desktop layout is handled purely
 * by Bootstrap's `.navbar-collapse` CSS (shown at >= 768px regardless of the
 * `in` class); this script only toggles the `in` class at mobile widths.
 *
 * Behavior:
 *   - Toggle button opens/closes the menu and keeps `aria-expanded` in sync.
 *   - Clicking a nav link closes the open menu.
 *   - Clicking outside the navbar closes the open menu.
 *   - Escape closes the open menu and returns focus to the toggle (a11y).
 *
 * Note: the previous version also added a `top-nav-scrolled` class on scroll
 * (no CSS rule existed for it — a no-op) and a jQuery-Easing "page-scroll"
 * smooth scroll that only targeted the logo's page URL (it errored and fell
 * through to normal navigation). Both were dead and have been dropped.
 */
(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    var toggle = document.querySelector('.navbar-toggle');
    var collapse = document.getElementById('navbar-main-collapse');
    if (!toggle || !collapse) {
      return;
    }

    function isOpen() {
      return collapse.classList.contains('in');
    }

    function openMenu() {
      collapse.classList.add('in');
      toggle.setAttribute('aria-expanded', 'true');
    }

    function closeMenu() {
      collapse.classList.remove('in');
      toggle.setAttribute('aria-expanded', 'false');
    }

    toggle.addEventListener('click', function (event) {
      event.preventDefault();
      if (isOpen()) {
        closeMenu();
      } else {
        openMenu();
      }
    });

    // Close the open mobile menu when a nav link inside it is clicked.
    collapse.addEventListener('click', function (event) {
      if (isOpen() && event.target.closest('a')) {
        closeMenu();
      }
    });

    // Close the open menu when clicking anywhere outside the navbar.
    document.addEventListener('click', function (event) {
      if (isOpen() && !event.target.closest('.navbar')) {
        closeMenu();
      }
    });

    // Close on Escape and restore focus to the toggle for keyboard users.
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && isOpen()) {
        closeMenu();
        toggle.focus();
      }
    });
  });
})();
