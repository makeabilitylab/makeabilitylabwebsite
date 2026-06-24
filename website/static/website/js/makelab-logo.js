/**
 * Makeability Lab Logo Animation Controller (Django Version)
 * 
 * See also: https://makeabilitylab.github.io/js/src/apps/makelogo/TriangleArtMorphTest2-MorphLib/
 * Code: https://github.com/makeabilitylab/js
 *
 * Sets up an interactive, scroll-driven logo animation on a canvas element.
 * As the user scrolls down the page, the logo morphs from its start state into
 * the assembled logo; scrolling back up returns to the start state.
 *
 * Default mode: triangles scatter from random positions and spiral inward to
 * assemble on scroll (see SPIRAL_TURNS / spiralPath).
 *
 * Easter egg: within the window of certain holidays, triangles morph from
 * holiday artwork (e.g., Santa, shamrock) into the logo instead.
 *
 * Features:
 *   - High-DPI (Retina) display support for crisp rendering
 *   - Responsive resizing via ResizeObserver
 *   - Smooth scroll-based animation using linear interpolation
 *   - Holiday art morphing easter egg
 *
 * Requirements:
 *   - A canvas element with ID 'makelab-logo-canvas'
 *   - A parent container with class 'col-md-6.center-canvas'
 *   - The MakeabilityLabLogoMorpher library from the CDN
 *   - Art JSON files in art_data/ alongside this script
 *
 * CDN Cache: You can purge the CDN cache at https://www.jsdelivr.com/tools/purge
 *
 * @author Jon Froehlich
 */
/**
 * 
 * Updated to use enhanced MakeabilityLabLogoMorpher features.
 */

import {
  MakeabilityLabLogo,
  MakeabilityLabLogoMorpher,
  TriangleArt,
  spiralPath,
} from 'https://cdn.jsdelivr.net/gh/makeabilitylab/js@main/dist/makelab.logo.js';

// =============================================================================
// Configuration
// =============================================================================

const MAX_HEIGHT = 600;
const TRIANGLE_SIZE = 70;
// Keep the assembled logo within this fraction of the canvas width so it never
// runs off-screen on narrow (mobile) viewports. See issue #1281.
const LOGO_WIDTH_FRACTION = 0.9;
const SCROLL_DISTANCE = 300;
// Trajectory the scattered triangles follow as they assemble into the logo.
// `turns` is the number of extra full revolutions each triangle sweeps around the
// logo centroid — higher = more swirl. See spiralPath() in the makelab js lib.
const SPIRAL_TURNS = 1;
const DPR = window.devicePixelRatio || 1;
const BG_FILL_COLOR = "rgba(255, 255, 255, 1)"; // Solid white for website clean look
const START_FILL_COLOR = "rgba(255, 255, 255, 0.5)";

const SCRIPT_BASE = new URL('.', import.meta.url).href;
const HOLIDAYS = [
  { month: 1,  day: 14, daysBefore: 7,  daysAfter: 1, file: 'heart.json' },
  { month: 2,  day: 17, daysBefore: 5,  daysAfter: 0, file: 'shamrock.json' },
  { month: 9,  day: 31, daysBefore: 10,  daysAfter: 0, file: 'jack-o-lantern.json' },
  { month: 11, day: 25, daysBefore: 21, daysAfter: 2, file: 'santa.json' },
];

// =============================================================================
// State & Canvas Setup
// =============================================================================

const canvas = document.getElementById('makelab-logo-canvas');
const ctx = canvas.getContext('2d');
const parentDiv = document.querySelector('.col-md-6.center-canvas');

// Honor prefers-reduced-motion (#1294): when set, the logo is rendered in its
// assembled END state (lerp = 1) and the scroll-driven morph is skipped — the
// logo is "stuck" fully assembled, no animation. Uses the shared helper
// (reduced-motion.js), querying live, with a matchMedia fallback.
function prefersReducedMotion() {
  if (window.MakeLab && window.MakeLab.prefersReducedMotion) {
    return window.MakeLab.prefersReducedMotion();
  }
  return !!(window.matchMedia &&
            window.matchMedia('(prefers-reduced-motion: reduce)').matches);
}

let logicalWidth, logicalHeight;
let morpher = null;
let isReady = false;
let cachedArtData = null;
// Reduced motion -> pin to the assembled end state; otherwise start scattered.
let currentLerpAmt = prefersReducedMotion() ? 1 : 0;

// The canvas markup labels itself "Animated ..."; drop "Animated" when the logo
// is rendered statically so the accessible name matches what's shown.
if (prefersReducedMotion()) {
  canvas.setAttribute('aria-label', 'Makeability Lab logo');
}

// =============================================================================
// Core Functions
// =============================================================================

function getActiveHolidayArtURL() {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  for (const h of HOLIDAYS) {
    const holiday = new Date(today.getFullYear(), h.month, h.day);
    const diffDays = (holiday - today) / (1000 * 60 * 60 * 24);
    if (diffDays <= h.daysBefore && diffDays >= -h.daysAfter) {
      return new URL(`art_data/${h.file}`, SCRIPT_BASE).href;
    }
  }
  return null;
}

/**
 * Syncs canvas dimensions and morpher layout.
 */
/**
 * Syncs canvas dimensions and morpher layout with responsive art scaling.
 */
async function initOrResize() {
  const rect = parentDiv.getBoundingClientRect();
  logicalWidth = rect.width;

  // Use the dynamic height instead of a static constant
  logicalHeight = getMaxHeight();

  canvas.style.width = logicalWidth + 'px';
  canvas.style.height = logicalHeight + 'px';
  canvas.width = logicalWidth * DPR;
  canvas.height = logicalHeight * DPR;
  ctx.setTransform(DPR, 0, 0, DPR, 0, 0);

  // Initialize Morpher if it doesn't exist
  if (!morpher) {
    morpher = new MakeabilityLabLogoMorpher(0, 0, TRIANGLE_SIZE, START_FILL_COLOR);
    // Swap the default straight-line (reverse-explosion) trajectory for a spiral
    // so the triangles swirl inward into place. pathFunction persists, and each
    // reset()/resetFromArt() below re-prepares per-triangle path data, so this
    // only needs to be set once at creation. See spiralPath() in the makelab lib.
    morpher.setPath(spiralPath({ turns: SPIRAL_TURNS }));
  }

  // Size the assembled logo so it always fits within the canvas width. On wide
  // (desktop) canvases this caps at the natural size (TRIANGLE_SIZE per cell);
  // on narrow (mobile) canvases it shrinks the logo so the final, unexploded
  // state stays fully on-screen. Must run before reset()/resetFromArt() below,
  // which read the logo's cell size to compute the morph end state. See #1281.
  const naturalLogoWidth = MakeabilityLabLogo.numCols * TRIANGLE_SIZE;
  const maxLogoWidth = logicalWidth * LOGO_WIDTH_FRACTION;
  morpher.setLogoSize(Math.min(naturalLogoWidth, maxLogoWidth));

  // Ensure the destination logo is centered in the final state
  morpher.centerLogo(logicalWidth, logicalHeight);

  // NEW: Define a dedicated gutter at the top for the artwork message text
  const messageGutter = logicalHeight < 400 ? 40 : 60;
  const availableHeightForArt = logicalHeight - messageGutter;

  const holidayUrl = getActiveHolidayArtURL();
  if (holidayUrl) {
    try {
      if (!cachedArtData) cachedArtData = await TriangleArt.loadData(holidayUrl);
      
      const padding = 0.9; 
      const horizontalScale = (logicalWidth * padding) / (cachedArtData.numCols * TRIANGLE_SIZE);
      const verticalScale = (availableHeightForArt * padding) / (cachedArtData.numRows * TRIANGLE_SIZE);
      
      const artScale = Math.min(1, horizontalScale, verticalScale);
      const artTriangleSize = TRIANGLE_SIZE * artScale;

      const artX = (logicalWidth - cachedArtData.numCols * artTriangleSize) / 2;
      
      // NEW: Offset the Y position by the messageGutter so the text has room above the heart
      const artY = messageGutter + (availableHeightForArt - cachedArtData.numRows * artTriangleSize) / 2;
      
      const art = new TriangleArt(artX, artY, artTriangleSize, cachedArtData);
      morpher.resetFromArt(art, logicalWidth, logicalHeight);
    } catch (e) {
      morpher.reset(logicalWidth, logicalHeight);
    }
  } else {
    morpher.reset(logicalWidth, logicalHeight);
  }

  isReady = true;
  morpher.update(currentLerpAmt);
  render();
}

/** 
 * Gets the maximum height allowed for the logo based on the CSS-defined container height.
 * This ensures mobile gets ~350px and desktop gets ~600px.
 */
function getMaxHeight() {
  const rect = parentDiv.getBoundingClientRect();
  return rect.height || 600; 
}

function render() {
  if (!isReady) return;
  ctx.fillStyle = BG_FILL_COLOR;
  ctx.fillRect(0, 0, logicalWidth, logicalHeight);
  morpher.draw(ctx);
}

// =============================================================================
// Handlers
// =============================================================================

// Scroll-driven morph — skipped entirely under reduced motion, where the logo
// stays pinned in its assembled end state (currentLerpAmt = 1). The
// ResizeObserver below still runs so the static logo stays correctly sized.
if (!prefersReducedMotion()) {
  window.addEventListener('scroll', () => {
    currentLerpAmt = Math.min(window.scrollY / SCROLL_DISTANCE, 1);
    if (morpher) {
      morpher.update(currentLerpAmt);
      render();
    }
  }, { passive: true });
}

const resizeObserver = new ResizeObserver(() => initOrResize());
resizeObserver.observe(parentDiv);

// Initial kick-off
initOrResize();