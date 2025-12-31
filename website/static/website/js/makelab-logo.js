/**
 * Makeability Lab Logo Animation Controller
 * 
 * Sets up an interactive, scroll-driven logo animation on a canvas element.
 * As the user scrolls down the page, the logo "explodes" into scattered triangles;
 * scrolling back up reassembles them.
 * 
 * Features:
 *   - High-DPI (Retina) display support for crisp rendering
 *   - Responsive resizing via ResizeObserver
 *   - Smooth scroll-based animation using linear interpolation
 * 
 * Requirements:
 *   - A canvas element with ID 'makelab-logo-canvas'
 *   - A parent container with class 'col-md-6.center-canvas'
 *   - The MakeabilityLabLogoExploder library from the CDN
 * 
 * CDN Cache: You can purge the CDN cache at https://www.jsdelivr.com/tools/purge
 * 
 * @file makelab-logo.js
 * @module makelab-logo
 * @author Jon Froehlich
 */

import { 
  MakeabilityLabLogoExploder, 
  MakeabilityLabLogo 
} from 'https://cdn.jsdelivr.net/gh/makeabilitylab/js@main/dist/makelab.logo.js';

// =============================================================================
// Configuration Constants
// =============================================================================

/** Maximum height of the logo canvas in logical pixels */
const MAX_HEIGHT = 350;

/** Initial width of the logo canvas in logical pixels */
const INITIAL_WIDTH = 500;

/** Size of individual triangles in the logo */
const TRIANGLE_SIZE = 70;

/** Scroll distance (in pixels) over which the full explosion animation occurs */
const SCROLL_DISTANCE_FOR_FULL_EXPLOSION = 300;

/** Device pixel ratio for high-DPI display support */
const DPR = window.devicePixelRatio || 1;

/** Background fill color (semi-transparent white for trail effect) */
const BG_FILL_COLOR = "rgba(255, 255, 255, 0.2)";

/** Initial fill color for triangles before animation */
const START_FILL_COLOR = "rgba(255, 255, 255, 0.5)";

// =============================================================================
// Canvas Setup
// =============================================================================

const canvas = document.getElementById('makelab-logo-canvas');
const ctx = canvas.getContext('2d');

// Track logical (CSS) dimensions separately from physical (buffer) dimensions.
// This distinction is crucial for high-DPI support: the canvas buffer is scaled
// up by DPR, but all drawing logic uses logical coordinates.
let logicalWidth = INITIAL_WIDTH;
let logicalHeight = MAX_HEIGHT;

// Initialize canvas with high-DPI support
setCanvasSize(logicalWidth, logicalHeight);

// =============================================================================
// Logo Exploder Initialization
// =============================================================================

// Calculate initial x position to center the logo horizontally
const initialXPos = logicalWidth / 2 - MakeabilityLabLogo.getWidth(TRIANGLE_SIZE) / 2;

const makeLabLogoExploder = new MakeabilityLabLogoExploder(
  initialXPos, 
  10,  // y offset from top
  TRIANGLE_SIZE, 
  START_FILL_COLOR
);

// Initialize explosion parameters and perform initial draw
makeLabLogoExploder.reset(logicalWidth, logicalHeight);
draw(ctx);

// Flag to track whether we need to reset animation params on next full explosion
let shouldResetOnFullExplosion = false;

// =============================================================================
// Event Handlers
// =============================================================================

window.addEventListener('scroll', handleScroll, { passive: true });

/**
 * Handles the scroll event to update the logo explosion animation.
 * 
 * The animation is driven by scroll position:
 *   - At scroll position 0: logo is fully assembled
 *   - At scroll position >= SCROLL_DISTANCE_FOR_FULL_EXPLOSION: logo is fully exploded
 * 
 * When the user scrolls back to full explosion after being partially assembled,
 * the explosion parameters are reset to create variety in the animation.
 */
function handleScroll() {
  const scrollY = window.scrollY;
  
  // Calculate interpolation amount (0 = assembled, 1 = fully exploded)
  const lerpAmount = Math.min(scrollY / SCROLL_DISTANCE_FOR_FULL_EXPLOSION, 1);

  makeLabLogoExploder.update(lerpAmount);
  draw(ctx);

  // Reset explosion parameters when returning to full explosion state.
  // This creates visual variety—each full explosion scatters differently.
  if (lerpAmount >= 1) {
    if (shouldResetOnFullExplosion) {
      makeLabLogoExploder.reset(logicalWidth, logicalHeight);
      shouldResetOnFullExplosion = false;
    }
  } else {
    // User has scrolled back; flag that we should reset on next full explosion
    shouldResetOnFullExplosion = true;
  }
}

// =============================================================================
// Responsive Resizing
// =============================================================================

const parentDiv = document.querySelector('.col-md-6.center-canvas');

const resizeObserver = new ResizeObserver(entries => {
  const parentDivRect = entries[0].contentRect;

  // Calculate new logical dimensions, respecting maximums
  const newLogicalWidth = parentDivRect.width;
  let newLogicalHeight = Math.min(parentDivRect.height, MAX_HEIGHT);

  // Update the logo to fit within new dimensions
  makeLabLogoExploder.fitToCanvas(newLogicalWidth, newLogicalHeight);

  // Update tracked logical dimensions
  logicalWidth = newLogicalWidth;
  logicalHeight = newLogicalHeight;

  // Resize canvas with high-DPI support
  setCanvasSize(logicalWidth, logicalHeight);

  // Re-center logo within new dimensions
  makeLabLogoExploder.centerLogo(logicalWidth, logicalHeight);

  draw(ctx);
});

resizeObserver.observe(parentDiv);

// =============================================================================
// Drawing Functions
// =============================================================================

/**
 * Sets the canvas size with proper high-DPI scaling.
 * 
 * On high-DPI displays (e.g., Retina), we need to:
 *   1. Set CSS size to the logical dimensions (what the user sees)
 *   2. Set buffer size to logical × devicePixelRatio (actual pixels)
 *   3. Scale the context so drawing code can use logical coordinates
 * 
 * @param {number} width - Logical width in CSS pixels
 * @param {number} height - Logical height in CSS pixels
 */
function setCanvasSize(width, height) {
  // CSS size controls the displayed size on screen
  canvas.style.width = width + 'px';
  canvas.style.height = height + 'px';

  // Buffer size is scaled up for sharp rendering on high-DPI displays
  canvas.width = width * DPR;
  canvas.height = height * DPR;

  // Scale context so all drawing operations use logical coordinates.
  // setTransform resets any existing transform before applying the new scale.
  ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
}

/**
 * Clears the canvas and draws the current state of the logo exploder.
 * 
 * Uses a semi-transparent fill to create a motion trail effect during animation.
 * 
 * @param {CanvasRenderingContext2D} ctx - The canvas 2D rendering context
 */
function draw(ctx) {
  // Clear canvas with semi-transparent fill (creates trail effect)
  ctx.fillStyle = BG_FILL_COLOR;
  ctx.fillRect(0, 0, logicalWidth, logicalHeight);
  
  makeLabLogoExploder.draw(ctx);

  // Uncomment for debugging:
  // drawDebugOverlay(ctx);
}

/**
 * Draws debug information overlay showing canvas and logo dimensions.
 * Useful for troubleshooting layout and scaling issues.
 * 
 * @param {CanvasRenderingContext2D} ctx - The canvas 2D rendering context
 */
function drawDebugOverlay(ctx) {
  const parentDivRect = parentDiv.getBoundingClientRect();

  ctx.fillStyle = 'black';
  ctx.font = '16px Arial';
  ctx.textAlign = 'center';

  // Logo dimensions (centered at bottom)
  const logoText = `Logo: ${makeLabLogoExploder.finalWidth.toFixed(1)} × ${makeLabLogoExploder.finalHeight.toFixed(1)}`;
  ctx.fillText(logoText, logicalWidth / 2, logicalHeight - 20);

  // Canvas and parent dimensions (centered at top)
  ctx.textBaseline = 'top';
  const canvasText = `Canvas: ${logicalWidth} × ${logicalHeight} (DPR: ${DPR}) | Parent: ${parentDivRect.width.toFixed(0)} × ${parentDivRect.height.toFixed(0)}`;
  ctx.fillText(canvasText, logicalWidth / 2, 4);
}