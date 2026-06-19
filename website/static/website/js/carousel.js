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
 *   - Honors prefers-reduced-motion: no autoplay, no looping hero video, and
 *     (via CSS) no crossfade. The video keeps its `autoplay` attribute so the
 *     no-JS baseline still plays it; this script pauses it when reduced motion
 *     is set. See issue #1294.
 *   - WCAG 2.2.2 (Pause, Stop, Hide): a visible `.carousel-motion-toggle`
 *     button (if present) pauses/plays BOTH the auto-advance and the hero video
 *     for all users — a discoverable mechanism, not just hover/focus.
 *   - Pauses while focus is inside the carousel (keyboard users reading links)
 *     and while the browser tab is hidden.
 *   - Marks the active indicator dot with aria-current.
 *
 * Note: there are no prev/next arrows or swipe gestures — this matches the
 * previous Bootstrap setup, which had neither.
 */
(function () {
  'use strict';

  // Shared helper (reduced-motion.js, loaded first). Query live so an OS toggle
  // mid-session is respected; fall back to false if the helper is missing.
  function prefersReducedMotion() {
    return !!(window.MakeLab && window.MakeLab.prefersReducedMotion
      ? window.MakeLab.prefersReducedMotion()
      : false);
  }

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

    // The user-facing motion state, governing BOTH the auto-advance and the
    // hero video. Starts paused when reduced motion is set, so under that
    // preference nothing moves and the toggle (if any) offers "Play". A user
    // can still explicitly opt into motion via the toggle (#1294).
    var motionPaused = prefersReducedMotion();

    function getActiveVideo() {
      var slide = slides[current];
      return slide ? slide.querySelector('video') : null;
    }

    function setVideoPlayback(video, shouldPlay) {
      if (!video) {
        return;
      }
      if (shouldPlay) {
        var playback = video.play();
        if (playback && playback.catch) {
          playback.catch(function () { /* autoplay blocked — ignore */ });
        }
      } else {
        video.pause();
      }
    }

    /**
     * Shows the slide at `index`, updates the indicator dots, and plays only
     * the active slide's video (if any) to avoid decoding hidden videos. The
     * active video plays only when motion is not paused (reduced motion / the
     * pause control), so the poster frame shows otherwise.
     */
    function render(index) {
      slides.forEach(function (slide, i) {
        var isActive = i === index;
        slide.classList.toggle('active', isActive);
        setVideoPlayback(slide.querySelector('video'), isActive && !motionPaused);
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

    /* ----------------------------- Autoplay ----------------------------- */

    var intervalAttr = root.getAttribute('data-interval');
    var interval = intervalAttr == null ? 5000 : parseInt(intervalAttr, 10);
    var pauseOnHover = root.getAttribute('data-pause') !== 'false';
    var multi = slides.length >= 2;

    var timer = null;
    var paused = false; // transient pause (hover / focus / tab hidden)

    function showNext() {
      render((current + 1) % slides.length);
    }

    function canPlay() {
      return multi && !motionPaused && interval > 0 && !paused && !document.hidden;
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

    /* --------------- Motion toggle (WCAG 2.2.2 Pause/Stop) --------------- */
    // A single discoverable control that pauses/plays both the auto-advance and
    // the looping hero video, for ALL users. Wired up regardless of slide count
    // so a single-banner looping video can still be paused. The button ships
    // `hidden` in the markup so no-JS users never see a dead control; we reveal
    // it only when there is actually motion to govern.

    var toggleBtn = root.querySelector('.carousel-motion-toggle');
    var hasVideo = slides.some(function (slide) {
      return !!slide.querySelector('video');
    });

    function updateToggleButton() {
      if (!toggleBtn) {
        return;
      }
      var label = motionPaused ? 'Play background motion' : 'Pause background motion';
      toggleBtn.setAttribute('aria-label', label);
      var sr = toggleBtn.querySelector('.sr-only');
      if (sr) {
        sr.textContent = label;
      }
      var icon = toggleBtn.querySelector('i');
      if (icon) {
        icon.classList.toggle('fa-play', motionPaused);
        icon.classList.toggle('fa-pause', !motionPaused);
      }
    }

    function toggleMotion() {
      motionPaused = !motionPaused;
      setVideoPlayback(getActiveVideo(), !motionPaused);
      if (motionPaused) {
        stop();
      } else {
        start();
      }
      updateToggleButton();
    }

    if (toggleBtn && (multi || hasVideo)) {
      toggleBtn.hidden = false;
      toggleBtn.addEventListener('click', toggleMotion);
      updateToggleButton();
    }

    /* ---------------------------- Indicators ---------------------------- */

    indicators.forEach(function (dot, i) {
      dot.addEventListener('click', function () {
        render(i);
        restart();
      });
    });

    /* -------------------------- Pause conditions ------------------------ */

    if (multi && pauseOnHover) {
      root.addEventListener('mouseenter', function () {
        paused = true;
        stop();
      });
      root.addEventListener('mouseleave', function () {
        paused = false;
        start();
      });
    }

    if (multi) {
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
    }

    // Initial paint + autoplay (start() is a no-op unless canPlay()).
    render(current);
    start();
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.carousel').forEach(setupCarousel);
  });
})();
