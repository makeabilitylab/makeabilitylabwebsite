/**
 * ============================================================================
 * PROJECT FILTER - Makeability Lab
 * ============================================================================
 *
 * Handles filtering of project cards by topic/umbrella category.
 * Supports both desktop sidebar buttons and mobile dropdown select.
 *
 * FEATURES:
 *   - Filter projects by topic category
 *   - Toggle filter on/off by clicking same filter
 *   - Keyboard accessible (all controls are focusable)
 *   - ARIA state management for screen readers
 *   - Live region announcements for filter changes
 *   - Smooth fade animations (respects prefers-reduced-motion)
 *   - Synced desktop/mobile filter controls
 *   - Empty state handling for sections with no matching projects
 *
 * USAGE:
 *   // Initialize after DOM is ready
 *   document.addEventListener('DOMContentLoaded', function() {
 *     ProjectFilter.init();
 *   });
 *
 * ACCESSIBILITY:
 *   - Uses aria-pressed for toggle button state
 *   - Live region announces filter changes
 *   - Focus management after filter reset
 *   - All interactive elements keyboard accessible
 *
 * @version 2.0.0
 * @author Makeability Lab
 * ============================================================================
 */

const ProjectFilter = (function() {
  'use strict';

  // ==========================================================================
  // PRIVATE STATE
  // ==========================================================================
  
  /** Currently active filter keyword, or null if no filter active */
  let activeFilter = null;
  
  /** Cache of DOM elements for performance */
  let elements = {
    filterButtons: null,
    resetButton: null,
    mobileSelect: null,
    liveRegion: null,
    projectCards: null,
    activeGrid: null,
    completedGrid: null,
    noActiveResults: null,
    noCompletedResults: null
  };

  /** Animation duration in milliseconds */
  const FADE_DURATION = 500; // Match with CSS transition duration for .project-card


  // ==========================================================================
  // INITIALIZATION
  // ==========================================================================

  /**
   * Initialize the project filter functionality.
   * Caches DOM elements and attaches event listeners.
   * 
   * @public
   */
  function init() {
    cacheElements();
    
    if (!elements.projectCards || elements.projectCards.length === 0) {
      console.warn('ProjectFilter: No project cards found');
      return;
    }

    attachEventListeners();
  }


  /**
   * Cache frequently accessed DOM elements.
   * 
   * @private
   */
  function cacheElements() {
    elements.filterButtons = document.querySelectorAll('.filter-btn');
    elements.resetButton = document.getElementById('filter-reset-btn');
    elements.mobileSelect = document.getElementById('filter-mobile-select');
    elements.liveRegion = document.getElementById('filter-live-region');
    elements.projectCards = document.querySelectorAll('.project-card');
    elements.activeGrid = document.getElementById('project-grid-active');
    elements.completedGrid = document.getElementById('project-grid-completed');
    elements.noActiveResults = document.getElementById('no-active-results');
    elements.noCompletedResults = document.getElementById('no-completed-results');
  }


  /**
   * Attach event listeners to filter controls.
   * 
   * @private
   */
  function attachEventListeners() {
    // Desktop filter buttons
    elements.filterButtons.forEach(function(button) {
      button.addEventListener('click', handleFilterButtonClick);
    });

    // Reset button
    if (elements.resetButton) {
      elements.resetButton.addEventListener('click', handleResetClick);
    }

    // Mobile dropdown
    if (elements.mobileSelect) {
      elements.mobileSelect.addEventListener('change', handleMobileSelectChange);
    }
  }


  // ==========================================================================
  // EVENT HANDLERS
  // ==========================================================================

  /**
   * Handle click on a filter button.
   * Toggles filter if already active, otherwise activates it.
   * 
   * @private
   * @param {Event} event - Click event
   */
  function handleFilterButtonClick(event) {
    const button = event.currentTarget;
    const filterKeyword = button.dataset.filter;

    if (activeFilter === filterKeyword) {
      // Same filter clicked - toggle off
      resetFilter();
    } else {
      // New filter clicked - apply it
      applyFilter(filterKeyword);
    }
  }


  /**
   * Handle click on the reset button.
   * 
   * @private
   */
  function handleResetClick() {
    resetFilter();
    
    // Move focus to first filter button for keyboard users
    if (elements.filterButtons && elements.filterButtons.length > 0) {
      elements.filterButtons[0].focus();
    }
  }


  /**
   * Handle change on the mobile select dropdown.
   * 
   * @private
   * @param {Event} event - Change event
   */
  function handleMobileSelectChange(event) {
    const selectedValue = event.target.value;
    
    if (selectedValue === '') {
      resetFilter();
    } else {
      applyFilter(selectedValue);
    }
  }


  // ==========================================================================
  // FILTER LOGIC
  // ==========================================================================

  /**
   * Apply a filter to show only matching projects.
   * 
   * @private
   * @param {string} filterKeyword - The filter keyword to apply
   */
  function applyFilter(filterKeyword) {
    activeFilter = filterKeyword;

    // Update button states
    updateButtonStates(filterKeyword);

    // Update mobile select to match
    syncMobileSelect(filterKeyword);

    // Show reset button
    showResetButton();

    // Filter the project cards with animation
    filterProjectCards(filterKeyword);

    // Announce change to screen readers
    announceFilterChange(filterKeyword);
  }


  /**
   * Reset the filter to show all projects.
   * 
   * @private
   */
  function resetFilter() {
    activeFilter = null;

    // Clear button states
    elements.filterButtons.forEach(function(button) {
      button.setAttribute('aria-pressed', 'false');
    });

    // Reset mobile select
    if (elements.mobileSelect) {
      elements.mobileSelect.value = '';
    }

    // Hide reset button
    hideResetButton();

    // Show all project cards with animation
    showAllProjectCards();

    // Hide empty state messages
    hideEmptyStates();

    // Announce change to screen readers
    announceFilterReset();
  }


  /**
   * Filter project cards based on keyword.
   * Uses fade animation that respects prefers-reduced-motion.
   * 
   * @private
   * @param {string} filterKeyword - The filter keyword to match
   */
  function filterProjectCards(filterKeyword) {
    let activeVisibleCount = 0;
    let completedVisibleCount = 0;

    elements.projectCards.forEach(function(card) {
      const keywords = card.dataset.projectKeywords || '';
      const matches = keywords.indexOf(filterKeyword) !== -1;
      const isInActiveGrid = elements.activeGrid && elements.activeGrid.contains(card);

      if (matches) {
        showCard(card);
        if (isInActiveGrid) {
          activeVisibleCount++;
        } else {
          completedVisibleCount++;
        }
      } else {
        hideCard(card);
      }
    });

    // Update empty state messages
    updateEmptyStates(activeVisibleCount, completedVisibleCount);
  }


  /**
   * Show all project cards (used when resetting filter).
   * 
   * @private
   */
  function showAllProjectCards() {
    elements.projectCards.forEach(function(card) {
      showCard(card);
    });
  }


  // ==========================================================================
  // CARD VISIBILITY
  // ==========================================================================

  /**
   * Show a project card with fade animation.
   * 
   * @private
   * @param {HTMLElement} card - The card element to show
   */
  function showCard(card) {
    // Remove hidden class immediately
    card.classList.remove('is-hidden');
    
    // Check if user prefers reduced motion
    if (prefersReducedMotion()) {
      card.classList.remove('is-fading');
      return;
    }

    // Trigger reflow to ensure transition works
    void card.offsetWidth;
    
    // Remove fading class to fade in
    card.classList.remove('is-fading');
  }


  /**
   * Hide a project card with fade animation.
   * 
   * @private
   * @param {HTMLElement} card - The card element to hide
   */
  function hideCard(card) {
    // Check if user prefers reduced motion
    if (prefersReducedMotion()) {
      card.classList.add('is-hidden');
      return;
    }

    // Add fading class to fade out
    card.classList.add('is-fading');
    
    // After animation, hide completely
    setTimeout(function() {
      if (card.classList.contains('is-fading')) {
        card.classList.add('is-hidden');
      }
    }, FADE_DURATION);
  }


  // ==========================================================================
  // UI UPDATES
  // ==========================================================================

  /**
   * Update filter button aria-pressed states.
   * 
   * @private
   * @param {string} activeKeyword - The currently active filter keyword
   */
  function updateButtonStates(activeKeyword) {
    elements.filterButtons.forEach(function(button) {
      const isActive = button.dataset.filter === activeKeyword;
      button.setAttribute('aria-pressed', isActive ? 'true' : 'false');
    });
  }


  /**
   * Sync the mobile select dropdown with the current filter.
   * 
   * @private
   * @param {string} filterKeyword - The current filter keyword
   */
  function syncMobileSelect(filterKeyword) {
    if (elements.mobileSelect) {
      elements.mobileSelect.value = filterKeyword || '';
    }
  }


  /**
   * Show the reset button.
   * 
   * @private
   */
  function showResetButton() {
    if (elements.resetButton) {
      elements.resetButton.style.display = 'flex';
    }
  }


  /**
   * Hide the reset button.
   * 
   * @private
   */
  function hideResetButton() {
    if (elements.resetButton) {
      elements.resetButton.style.display = 'none';
    }
  }


  /**
   * Update empty state messages based on visible card counts.
   * 
   * @private
   * @param {number} activeCount - Number of visible active project cards
   * @param {number} completedCount - Number of visible completed project cards
   */
  function updateEmptyStates(activeCount, completedCount) {
    if (elements.noActiveResults) {
      elements.noActiveResults.style.display = activeCount === 0 ? 'block' : 'none';
    }
    if (elements.noCompletedResults) {
      elements.noCompletedResults.style.display = completedCount === 0 ? 'block' : 'none';
    }
  }


  /**
   * Hide all empty state messages.
   * 
   * @private
   */
  function hideEmptyStates() {
    if (elements.noActiveResults) {
      elements.noActiveResults.style.display = 'none';
    }
    if (elements.noCompletedResults) {
      elements.noCompletedResults.style.display = 'none';
    }
  }


  // ==========================================================================
  // ACCESSIBILITY
  // ==========================================================================

  /**
   * Announce filter change to screen readers via live region.
   * 
   * @private
   * @param {string} filterKeyword - The applied filter keyword
   */
  function announceFilterChange(filterKeyword) {
    if (elements.liveRegion) {
      // Count visible cards after a brief delay for animation
      setTimeout(function() {
        const visibleCount = document.querySelectorAll('.project-card:not(.is-hidden)').length;
        elements.liveRegion.textContent = 
          'Filtered by ' + filterKeyword + '. Showing ' + visibleCount + ' project' + 
          (visibleCount === 1 ? '' : 's') + '.';
      }, FADE_DURATION + 50);
    }
  }


  /**
   * Announce filter reset to screen readers via live region.
   * 
   * @private
   */
  function announceFilterReset() {
    if (elements.liveRegion) {
      const totalCount = elements.projectCards.length;
      elements.liveRegion.textContent = 
        'Filter cleared. Showing all ' + totalCount + ' projects.';
    }
  }


  /**
   * Check if user prefers reduced motion.
   * 
   * @private
   * @returns {boolean} True if user prefers reduced motion
   */
  function prefersReducedMotion() {
    return window.matchMedia && 
           window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }


  // ==========================================================================
  // PUBLIC API
  // ==========================================================================

  return {
    init: init,
    
    /**
     * Programmatically apply a filter.
     * 
     * @public
     * @param {string} filterKeyword - The filter keyword to apply
     * 
     * @example
     * ProjectFilter.setFilter('Accessibility');
     */
    setFilter: function(filterKeyword) {
      if (filterKeyword) {
        applyFilter(filterKeyword);
      } else {
        resetFilter();
      }
    },

    /**
     * Programmatically reset the filter.
     * 
     * @public
     * 
     * @example
     * ProjectFilter.reset();
     */
    reset: resetFilter,

    /**
     * Get the currently active filter keyword.
     * 
     * @public
     * @returns {string|null} The active filter keyword, or null if no filter active
     * 
     * @example
     * const current = ProjectFilter.getActiveFilter();
     * console.log(current); // 'Accessibility' or null
     */
    getActiveFilter: function() {
      return activeFilter;
    }
  };

})();