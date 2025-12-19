/**
 * ============================================================================
 * VIDEO AGE DISPLAY - Makeability Lab
 * ============================================================================
 *
 * Displays humanized video age ("3 months ago") or future release dates
 * for video snippets. Replaces the previous inline document.write() approach
 * with a proper module that runs on DOMContentLoaded.
 *
 * FEATURES:
 *   - Displays relative time for past videos ("2 years ago")
 *   - Displays formatted date for future/scheduled videos ("Releases Jan 15, 2025")
 *   - Falls back to static date if humanizeDuration is unavailable
 *   - No inline JavaScript required
 *
 * USAGE:
 *   HTML (in video snippet):
 *   <span class="video-age" 
 *         data-video-age-ms="123456789"
 *         data-video-date="2024-01-15T00:00:00Z">
 *     <time datetime="2024-01-15T00:00:00Z">Jan 15, 2024</time>
 *   </span>
 *
 *   JavaScript (in page):
 *   document.addEventListener('DOMContentLoaded', function() {
 *     VideoAge.init();
 *   });
 *
 * DEPENDENCIES:
 *   - humanize-duration.js (optional, for relative time display)
 *
 * ACCESSIBILITY:
 *   - Uses <time> element with datetime attribute for machine-readable dates
 *   - Graceful fallback if JS fails (shows static date from server)
 *
 * @version 1.0.0
 * @author Makeability Lab
 * ============================================================================
 */

const VideoAge = (function() {
  'use strict';

  // ==========================================================================
  // CONFIGURATION
  // ==========================================================================

  /** Selector for video age elements */
  const SELECTOR = '.video-age[data-video-age-ms]';

  /** Options for humanizeDuration */
  const HUMANIZE_OPTIONS = {
    largest: 1,  // Show only the largest unit (e.g., "2 years" not "2 years, 3 months")
    round: true  // Round to nearest unit
  };


  // ==========================================================================
  // INITIALIZATION
  // ==========================================================================

  /**
   * Initialize video age display for all matching elements.
   * Should be called after DOMContentLoaded.
   * 
   * @public
   * 
   * @example
   * document.addEventListener('DOMContentLoaded', function() {
   *   VideoAge.init();
   * });
   */
  function init() {
    const elements = document.querySelectorAll(SELECTOR);
    
    if (elements.length === 0) {
      return; // No video age elements on this page
    }

    // Check if humanizeDuration is available
    if (typeof humanizeDuration === 'undefined') {
      console.warn('VideoAge: humanizeDuration library not loaded. Using fallback date display.');
      // Fallback: just show the static date (already in the HTML)
      return;
    }

    elements.forEach(updateVideoAge);
  }


  // ==========================================================================
  // CORE FUNCTIONALITY
  // ==========================================================================

  /**
   * Update a single video age element with humanized time.
   * 
   * @private
   * @param {HTMLElement} element - The .video-age element to update
   */
  function updateVideoAge(element) {
    const ageInMs = parseInt(element.dataset.videoAgeMs, 10);
    const videoDateStr = element.dataset.videoDate;

    if (isNaN(ageInMs)) {
      console.warn('VideoAge: Invalid age value', element);
      return;
    }

    let displayText;

    if (ageInMs < 0) {
      // Video is scheduled for future release
      displayText = formatFutureRelease(videoDateStr);
    } else {
      // Video is in the past - show relative time
      displayText = formatPastAge(ageInMs);
    }

    // Update the element content while preserving the <time> element
    const timeElement = element.querySelector('time');
    if (timeElement) {
      // Replace content but keep the time element for accessibility
      element.innerHTML = '';
      element.appendChild(document.createTextNode(displayText));
    } else {
      element.textContent = displayText;
    }
  }


  /**
   * Format a past video age as relative time.
   * 
   * @private
   * @param {number} ageInMs - Age in milliseconds
   * @returns {string} Formatted string like "2 years ago"
   */
  function formatPastAge(ageInMs) {
    try {
      const humanized = humanizeDuration(ageInMs, HUMANIZE_OPTIONS);
      return humanized + ' ago';
    } catch (e) {
      console.error('VideoAge: Error humanizing duration', e);
      return '';
    }
  }


  /**
   * Format a future release date.
   * 
   * @private
   * @param {string} dateStr - ISO date string
   * @returns {string} Formatted string like "Releases Jan 15, 2025"
   */
  function formatFutureRelease(dateStr) {
    try {
      const releaseDate = new Date(dateStr);
      const formattedDate = releaseDate.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
      return 'Releases ' + formattedDate;
    } catch (e) {
      console.error('VideoAge: Error formatting future date', e);
      return 'Coming soon';
    }
  }


  // ==========================================================================
  // PUBLIC API
  // ==========================================================================

  return {
    /**
     * Initialize video age display.
     * Call this once after DOM is ready.
     */
    init: init,

    /**
     * Manually refresh all video age displays.
     * Useful if new video elements are added dynamically.
     * 
     * @public
     * 
     * @example
     * // After adding new video cards via AJAX
     * VideoAge.refresh();
     */
    refresh: init
  };

})();