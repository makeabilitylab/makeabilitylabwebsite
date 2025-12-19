/**
 * ============================================================================
 * SWAP IMAGE - Makeability Lab
 * ============================================================================
 *
 * Easter egg functionality that swaps person photos on mouse hover.
 * When users hover over a team member's photo, it swaps to an alternate
 * "fun" image, then swaps back when the mouse leaves.
 *
 * FEATURES:
 *   - Event delegation for better performance (no inline handlers)
 *   - Toggle functionality via console API
 *   - Respects images without alternate sources
 *   - Clean module pattern with no global pollution
 *
 * USAGE:
 *   HTML:
 *   <img class="swap-image"
 *        src="/path/to/primary.jpg"
 *        data-alt-src="/path/to/alternate.jpg"
 *        alt="Person Name">
 *
 *   JavaScript:
 *   document.addEventListener('DOMContentLoaded', function() {
 *     SwapImage.init();
 *   });
 *
 * CONSOLE API (for debugging/fun):
 *   SwapImage.enable()    - Turn on image swapping
 *   SwapImage.disable()   - Turn off image swapping
 *   SwapImage.toggle()    - Toggle image swapping on/off
 *   SwapImage.isEnabled   - Check if swapping is currently enabled (getter)
 *
 * ACCESSIBILITY:
 *   This is a visual-only easter egg and does not affect keyboard navigation
 *   or screen reader experience. The alt text remains unchanged during swap.
 *
 * @version 2.0.0 - Refactored with event delegation and module pattern
 * @author Makeability Lab
 * ============================================================================
 */

const SwapImage = (function() {
  'use strict';

  // ==========================================================================
  // PRIVATE STATE
  // ==========================================================================

  /** Whether image swapping is currently enabled */
  let enabled = true;

  /** Selector for swappable images */
  const SELECTOR = '.swap-image';


  // ==========================================================================
  // INITIALIZATION
  // ==========================================================================

  /**
   * Initialize the swap image functionality.
   * Sets up event delegation on the document for mouseenter/mouseleave events.
   * 
   * @public
   * 
   * @example
   * document.addEventListener('DOMContentLoaded', function() {
   *   SwapImage.init();
   * });
   */
  function init() {
    // Use capture phase for event delegation with mouseenter/mouseleave
    // These events don't bubble, so we need capture: true
    document.addEventListener('mouseenter', handleMouseEnter, true);
    document.addEventListener('mouseleave', handleMouseLeave, true);

    // Friendly console message for curious developers
    console.log(
      "Hi console friends 👋🏽\n\n" +
      "Spotted our easter egg? You can control it:\n" +
      "  SwapImage.disable()  – Turn off image swapping\n" +
      "  SwapImage.enable()   – Turn it back on\n" +
      "  SwapImage.toggle()   – Toggle on/off\n" +
      "  SwapImage.isEnabled  – Check current state\n"
    );
  }


  // ==========================================================================
  // EVENT HANDLERS
  // ==========================================================================

  /**
   * Handle mouseenter events on swap-image elements.
   * Swaps to the alternate image when mouse enters.
   * 
   * @private
   * @param {MouseEvent} event - The mouseenter event
   */
  function handleMouseEnter(event) {
    if (!enabled) return;
    
    const target = event.target;
    if (target.matches && target.matches(SELECTOR)) {
      swapImageSource(target);
    }
  }


  /**
   * Handle mouseleave events on swap-image elements.
   * Swaps back to the original image when mouse leaves.
   * 
   * @private
   * @param {MouseEvent} event - The mouseleave event
   */
  function handleMouseLeave(event) {
    if (!enabled) return;
    
    const target = event.target;
    if (target.matches && target.matches(SELECTOR)) {
      swapImageSource(target);
    }
  }


  // ==========================================================================
  // CORE FUNCTIONALITY
  // ==========================================================================

  /**
   * Swap an image's src with its data-alt-src value.
   * The swap is bidirectional - calling twice restores the original.
   * 
   * @private
   * @param {HTMLImageElement} imgElement - The image element to swap
   */
  function swapImageSource(imgElement) {
    const altSrc = imgElement.dataset.altSrc;
    
    // Only swap if there's an alternate source defined
    if (altSrc) {
      // Store current src in data attribute
      imgElement.dataset.altSrc = imgElement.src;
      // Set new src from what was in data attribute
      imgElement.src = altSrc;
    }
  }


  // ==========================================================================
  // PUBLIC API
  // ==========================================================================

  return {
    /**
     * Initialize swap image functionality.
     * Call this once after DOM is ready.
     */
    init: init,

    /**
     * Enable image swapping.
     * 
     * @example
     * SwapImage.enable();
     */
    enable: function() {
      enabled = true;
      console.log('🖼️ Swap image enabled.');
    },

    /**
     * Disable image swapping.
     * Images will remain static on hover.
     * 
     * @example
     * SwapImage.disable();
     */
    disable: function() {
      enabled = false;
      console.log('🖼️ Swap image disabled.');
    },

    /**
     * Toggle image swapping on/off.
     * 
     * @returns {boolean} The new enabled state
     * 
     * @example
     * SwapImage.toggle(); // Returns true or false
     */
    toggle: function() {
      enabled = !enabled;
      console.log('🖼️ Swap image ' + (enabled ? 'enabled' : 'disabled') + '.');
      return enabled;
    },

    /**
     * Check if image swapping is currently enabled.
     * 
     * @type {boolean}
     * @readonly
     * 
     * @example
     * if (SwapImage.isEnabled) {
     *   console.log('Swapping is on!');
     * }
     */
    get isEnabled() {
      return enabled;
    }
  };

})();