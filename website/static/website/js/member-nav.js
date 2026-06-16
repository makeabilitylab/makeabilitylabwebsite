/**
 * MemberNav — navigation aids for long member pages (#1110).
 *
 * Two pieces, both progressive enhancements:
 *   1. Section nav scroll-spy. The server renders a sticky <nav> linking to the
 *      sections that exist; this highlights the one you're currently viewing
 *      (aria-current + an active class) via IntersectionObserver. The links work
 *      without JS — this only adds the highlight.
 *   2. A floating "Back to top" button, injected here (so a no-JS page doesn't
 *      show a dead control). It appears once you've scrolled down a screenful or
 *      two and smooth-scrolls to the top (respecting prefers-reduced-motion).
 *
 * It also measures the fixed site navbar's height into the --ml-navbar-height
 * CSS variable so the sticky section nav can sit just below it and anchor jumps
 * land below both (see scroll-margin-top in member.css).
 *
 * @author Makeability Lab
 */
const MemberNav = (function () {
  'use strict';

  function reducedMotion() {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  /** Publish the fixed navbar's height so CSS can offset the sticky nav and
   *  anchor targets. Re-measured on resize (the navbar's height changes across
   *  breakpoints). */
  function trackNavbarHeight() {
    const navbar = document.querySelector('.navbar-fixed-top');
    const apply = function () {
      const h = navbar ? navbar.offsetHeight : 0;
      document.documentElement.style.setProperty('--ml-navbar-height', h + 'px');
    };
    apply();
    window.addEventListener('resize', apply);
  }

  function setupScrollSpy(nav) {
    const links = Array.prototype.slice.call(
      nav.querySelectorAll('[data-section-link]')
    );
    const sections = links
      .map(function (link) { return document.getElementById(link.dataset.sectionLink); })
      .filter(Boolean);
    if (sections.length === 0 || !('IntersectionObserver' in window)) {
      return;
    }

    const setActive = function (id) {
      links.forEach(function (link) {
        const isActive = link.dataset.sectionLink === id;
        link.classList.toggle('is-active', isActive);
        if (isActive) {
          link.setAttribute('aria-current', 'location');
        } else {
          link.removeAttribute('aria-current');
        }
      });
    };

    const visible = new Set();
    const observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          visible.add(entry.target);
        } else {
          visible.delete(entry.target);
        }
      });
      // Highlight the topmost section (in DOM order) currently in the band.
      for (let i = 0; i < sections.length; i += 1) {
        if (visible.has(sections[i])) {
          setActive(sections[i].id);
          return;
        }
      }
    }, {
      // A thin band a bit below the sticky chrome; -55% bottom keeps a single
      // section active rather than several at once.
      rootMargin: '-25% 0px -55% 0px',
      threshold: 0,
    });

    sections.forEach(function (section) { observer.observe(section); });
  }

  /** Reveal the person's name in the sticky nav once the page <h1> scrolls up
   *  behind the sticky chrome, and hide it again when the <h1> is back in view. */
  function setupNavName(nav) {
    const nameEl = nav.querySelector('[data-nav-name]');
    const heading = document.querySelector('.person-name-header');
    if (!nameEl || !heading || !('IntersectionObserver' in window)) {
      return;
    }
    const navbar = document.querySelector('.navbar-fixed-top');
    const topOffset = (navbar ? navbar.offsetHeight : 0) + nav.offsetHeight;
    const observer = new IntersectionObserver(function (entries) {
      // Show the nav name exactly when the heading is NOT visible below the
      // fixed navbar + sticky nav.
      nameEl.hidden = entries[0].isIntersecting;
    }, { rootMargin: '-' + topOffset + 'px 0px 0px 0px', threshold: 0 });
    observer.observe(heading);
  }

  /** Keep every "loaded/total" count (both the sticky-nav links AND the section
   *  headings) in sync with its grid as cards are appended by "Load more" /
   *  "Load all". Count elements opt in with [data-artifact-count] and point at
   *  their grid via data-count-grid; several can share one grid (nav + header),
   *  so we group by grid and run a single observer per grid. Sections that never
   *  overflow have no live grid and keep their static server value. */
  function setupCounts() {
    if (!('MutationObserver' in window)) {
      return;
    }
    const spans = Array.prototype.slice.call(
      document.querySelectorAll('[data-artifact-count]')
    );
    const byGrid = {};
    spans.forEach(function (span) {
      const id = span.dataset.countGrid;
      (byGrid[id] = byGrid[id] || []).push(span);
    });
    Object.keys(byGrid).forEach(function (gridId) {
      const grid = document.getElementById(gridId);
      if (!grid) {
        return; // no live grid -> the server's static loaded==total stands
      }
      const group = byGrid[gridId];
      const update = function () {
        const n = grid.childElementCount;
        group.forEach(function (span) {
          span.textContent = '(' + n + '/' + span.dataset.countTotal + ')';
        });
      };
      update();
      new MutationObserver(update).observe(grid, { childList: true });
    });
  }

  function setupBackToTop() {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'back-to-top';
    button.setAttribute('aria-label', 'Back to top');
    button.hidden = true;
    button.innerHTML = '<i class="fa-solid fa-arrow-up" aria-hidden="true"></i>';
    document.body.appendChild(button);

    button.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: reducedMotion() ? 'auto' : 'smooth' });
      // Return focus to the document start for keyboard users.
      const main = document.querySelector('main, h1') || document.body;
      if (main && typeof main.focus === 'function') {
        main.setAttribute('tabindex', '-1');
        main.focus({ preventScroll: true });
      }
    });

    // Reveal once the reader has scrolled down past roughly half a screen, so
    // it shows up on genuinely long pages but never on short ones (where the
    // page can't scroll that far).
    const THRESHOLD = 400;
    let ticking = false;
    const onScroll = function () {
      if (ticking) {
        return;
      }
      ticking = true;
      window.requestAnimationFrame(function () {
        button.hidden = window.scrollY < THRESHOLD;
        ticking = false;
      });
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  function init() {
    trackNavbarHeight();
    const nav = document.querySelector('[data-member-section-nav]');
    if (nav) {
      setupScrollSpy(nav);
      setupNavName(nav);
    }
    setupCounts();
    setupBackToTop();
  }

  return { init: init };
})();
