/*!
 * Carousel — vanilla JS, no jQuery / Bootstrap JS.
 *
 * Auto-rotating crossfade banner with clickable indicator dots, replacing
 * Bootstrap 3's carousel plugin (Track A, see issues #1288 / #1253). It works
 * with the existing markup: a `.carousel` containing `.carousel-inner > .item`
 * slides (one marked `.active`) and an optional `.carousel-indicators > li`
 * dot list. The crossfade itself is pure CSS (carousel_fade.css); this script
 * only moves the `.active` class and runs the autoplay timer.
 *
 * Per-carousel options (data attributes on the `.carousel` element):
 *   - data-interval: autoplay delay in ms (default 5000; <= 0 disables autoplay).
 *   - data-pause="false": do NOT pause on mouse hover (default is to pause).
 *
 * Accessibility:
 *   - Honors prefers-reduced-motion: no autoplay and (via CSS) no crossfade.
 *   - Pauses while focus is inside the carousel (keyboard users reading links)
 *     and while the browser tab is hidden.
 *   - Marks the active indicator dot with aria-current.
 *
 * Note: there are no prev/next arrows or swipe gestures — this matches the
 * previous Bootstrap setup, which had neither.
 */
(function () {
  'use strict';

  var prefersReducedMotion = window.matchMedia
    ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
    : false;

  function setupCarousel(root) {
    var inner = root.querySelector('.carousel-inner');
    if (!inner) {
      return;
    }

    var slides = Array.prototype.slice.call(inner.querySelectorAll(':scope > .item'));
    if (slides.length === 0) {
      return;
    }

    var indicators = Array.prototype.slice.call(
      root.querySelectorAll('.carousel-indicators > li')
    );

    // Start from whichever slide the template marked active (default first).
    var current = slides.findIndex(function (slide) {
      return slide.classList.contains('active');
    });
    if (current < 0) {
      current = 0;
    }

    /**
     * Shows the slide at `index`, updates the indicator dots, and plays only
     * the active slide's video (if any) to avoid decoding hidden videos.
     */
    function render(index) {
      slides.forEach(function (slide, i) {
        var isActive = i === index;
        slide.classList.toggle('active', isActive);

        var video = slide.querySelector('video');
        if (video) {
          if (isActive) {
            var playback = video.play();
            if (playback && playback.catch) {
              playback.catch(function () { /* autoplay blocked — ignore */ });
            }
          } else {
            video.pause();
          }
        }
      });

      indicators.forEach(function (dot, i) {
        var isActive = i === index;
        dot.classList.toggle('active', isActive);
        if (isActive) {
          dot.setAttribute('aria-current', 'true');
        } else {
          dot.removeAttribute('aria-current');
        }
      });

      current = index;
    }

    render(current);

    // A single slide has nothing to rotate or navigate.
    if (slides.length < 2) {
      return;
    }

    /* ----------------------------- Autoplay ----------------------------- */

    var intervalAttr = root.getAttribute('data-interval');
    var interval = intervalAttr == null ? 5000 : parseInt(intervalAttr, 10);
    var pauseOnHover = root.getAttribute('data-pause') !== 'false';

    var timer = null;
    var paused = false;

    function showNext() {
      render((current + 1) % slides.length);
    }

    function canPlay() {
      return !prefersReducedMotion && interval > 0 && !paused && !document.hidden;
    }

    function start() {
      stop();
      if (canPlay()) {
        timer = window.setInterval(showNext, interval);
      }
    }

    function stop() {
      if (timer !== null) {
        window.clearInterval(timer);
        timer = null;
      }
    }

    function restart() {
      // After a manual jump, give the next auto-advance a full interval.
      stop();
      start();
    }

    /* ---------------------------- Indicators ---------------------------- */

    indicators.forEach(function (dot, i) {
      dot.addEventListener('click', function () {
        render(i);
        restart();
      });
    });

    /* -------------------------- Pause conditions ------------------------ */

    if (pauseOnHover) {
      root.addEventListener('mouseenter', function () {
        paused = true;
        stop();
      });
      root.addEventListener('mouseleave', function () {
        paused = false;
        start();
      });
    }

    // Pause while focus is inside the carousel (keyboard users on slide links).
    root.addEventListener('focusin', function () {
      paused = true;
      stop();
    });
    root.addEventListener('focusout', function (event) {
      if (!root.contains(event.relatedTarget)) {
        paused = false;
        start();
      }
    });

    // Pause when the tab is hidden; resume when it becomes visible again.
    document.addEventListener('visibilitychange', function () {
      if (document.hidden) {
        stop();
      } else {
        start();
      }
    });

    start();
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.carousel').forEach(setupCarousel);
  });
})();
