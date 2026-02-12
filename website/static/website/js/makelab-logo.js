/**
 * Makeability Lab Logo Animation Controller
 *
 * Sets up an interactive, scroll-driven logo animation on a canvas element.
 * As the user scrolls down the page, the logo "explodes" into scattered triangles;
 * scrolling back up reassembles them.
 *
 * Easter egg: within the window of certain holidays, the triangles morph from
 * holiday artwork (e.g., Santa, shamrock) into the logo rather than scattering
 * from random positions.
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
 *   - The MakeabilityLabLogoExploder library from the CDN
 *   - Art JSON files in art_data/ alongside this script
 *
 * CDN Cache: You can purge the CDN cache at https://www.jsdelivr.com/tools/purge
 *
 * @file makelab-logo.js
 * @module makelab-logo
 * @author Jon Froehlich
 */

import {
  MakeabilityLabLogoExploder,
  MakeabilityLabLogo,
  Triangle,
  TriangleArt,
  shuffle,
} from 'https://cdn.jsdelivr.net/gh/makeabilitylab/js@main/dist/makelab.all.min.js';

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

/** Initial fill color for triangles before animation (used in random explosion mode only) */
const START_FILL_COLOR = "rgba(255, 255, 255, 0.5)";

// =============================================================================
// Holiday Easter Egg Configuration
// =============================================================================

/**
 * Base URL for resolving art_data JSON files relative to this script's location.
 * Works because this file is loaded as type="module".
 */
const SCRIPT_BASE = new URL('.', import.meta.url).href;

/**
 * Holiday definitions. month is 0-indexed (JS Date convention).
 * daysBefore and daysAfter are both inclusive.
 */
const HOLIDAYS = [
  { month: 1,  day: 14, daysBefore: 5,  daysAfter: 1, file: 'heart.json' },         // Valentine's Day
  { month: 2,  day: 17, daysBefore: 5,  daysAfter: 0, file: 'shamrock.json' },       // St. Patrick's Day
  { month: 9,  day: 31, daysBefore: 7,  daysAfter: 0, file: 'jack-o-lantern.json' }, // Halloween
  { month: 11, day: 25, daysBefore: 21, daysAfter: 2, file: 'santa.json' },          // Christmas
];

/**
 * Returns the full URL of the active holiday art JSON file, or null if no
 * holiday window is currently active. First match wins.
 *
 * @returns {string|null}
 */
function getActiveHolidayArtURL() {
  const now   = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());

  for (const h of HOLIDAYS) {
    const holiday  = new Date(today.getFullYear(), h.month, h.day);
    const diffDays = (holiday - today) / (1000 * 60 * 60 * 24); // positive = future

    if (diffDays <= h.daysBefore && diffDays >= -h.daysAfter) {
      return new URL(`art_data/${h.file}`, SCRIPT_BASE).href;
    }
  }
  return null;
}

// =============================================================================
// Canvas Setup
// =============================================================================

const canvas = document.getElementById('makelab-logo-canvas');
const ctx = canvas.getContext('2d');

// Track logical (CSS) dimensions separately from physical (buffer) dimensions.
let logicalWidth  = INITIAL_WIDTH;
let logicalHeight = MAX_HEIGHT;

setCanvasSize(logicalWidth, logicalHeight);

// =============================================================================
// Logo Exploder Initialization
// =============================================================================

const initialXPos = logicalWidth / 2 - MakeabilityLabLogo.getGridWidth(TRIANGLE_SIZE) / 2;

const makeLabLogoExploder = new MakeabilityLabLogoExploder(
  initialXPos,
  10,
  TRIANGLE_SIZE,
  START_FILL_COLOR
);

// Attempt to load holiday art; fall back to standard random explosion
const holidayArtURL = getActiveHolidayArtURL();

if (holidayArtURL) {
  initWithHolidayArt(holidayArtURL);
} else {
  makeLabLogoExploder.reset(logicalWidth, logicalHeight);
  draw(ctx);
}

// Flag to track whether we need to reset animation params on next full explosion
let shouldResetOnFullExplosion = false;

// Cache for loaded holiday art data to avoid refetching on every reset
let cachedArtData = null;

// =============================================================================
// Holiday Art Initialization
// =============================================================================

/**
 * Loads holiday art JSON and seeds the exploder's start state from the art's
 * triangle positions and colors, so the animation morphs from art → logo
 * rather than scattering from random positions.
 *
 * Falls back to standard random explosion if the fetch fails.
 *
 * @param {string} url - Full URL to the art JSON file.
 */
async function initWithHolidayArt(url) {
  try {
    if (!cachedArtData) {
      cachedArtData = await TriangleArt.loadData(url);
    }
    // Recompute position fresh each time (handles resize correctly)
    const artX = logicalWidth  / 2 - (cachedArtData.numCols * TRIANGLE_SIZE) / 2;
    const artY = logicalHeight / 2 - (cachedArtData.numRows * TRIANGLE_SIZE) / 2;
    const art  = new TriangleArt(artX, artY, TRIANGLE_SIZE, cachedArtData);

    resetExploderFromArt(art);
  } catch (e) {
    console.warn('Holiday art failed to load, falling back to random explosion:', e);
    makeLabLogoExploder.reset(logicalWidth, logicalHeight);
  }
  draw(ctx);
}

/**
 * Seeds the exploder's originalRandomTriLocs from a TriangleArt instance,
 * matching triangles by direction (so morph geometry stays clean).
 *
 * Any logo triangles with no matching art source (direction mismatch or count
 * overflow) fall back to a random position, matching the standard reset() behavior.
 *
 * This is intentionally implemented here rather than in the library so it can
 * stay in sync with TriangleArt without requiring a library release.
 *
 * @param {TriangleArt} art
 */
function resetExploderFromArt(art) {
  // Use the exploder's internal logo as the end-state reference
  const logoTriangles = makeLabLogoExploder.makeLabLogo.getAllTriangles();
  const animTriangles = makeLabLogoExploder.makeLabLogoAnimated.getAllTriangles();
  const endStateSize  = makeLabLogoExploder.makeLabLogo.cellSize;

  // Group art source triangles by direction
  const sourceTris = art.getAllTriangles();
  const sourceByDir = new Map();
  for (const tri of sourceTris) {
    if (!sourceByDir.has(tri.direction)) sourceByDir.set(tri.direction, []);
    sourceByDir.get(tri.direction).push(tri);
  }

  // Shuffle each direction group for visual variety (matches sketch.js behavior)
  for (const group of sourceByDir.values()) shuffle(group);

  // Track how many from each direction group we've consumed
  const dirIndex = new Map();

  makeLabLogoExploder.originalRandomTriLocs = [];

  for (let i = 0; i < animTriangles.length; i++) {
    const logoTri  = logoTriangles[i];
    const animTri  = animTriangles[i];
    const dir      = logoTri.direction;
    const sources  = sourceByDir.get(dir);

    let startX, startY, startFill, startStroke, startSize, startAngle, startStrokeWidth;

    if (sources && sources.length > 0) {
      // Consume source triangles round-robin within this direction
      const idx = (dirIndex.get(dir) ?? 0) % sources.length;
      dirIndex.set(dir, idx + 1);
      const src = sources[idx];

      startX           = src.x;
      startY           = src.y;
      startFill        = src.fillColor;
      startStroke      = src.strokeColor;
      startSize        = src.size ?? endStateSize;
      startAngle       = 0; // art is flat; no rotation needed
      startStrokeWidth = animTri.strokeWidth;
    } else {
      // Fallback: random position (standard explosion behavior)
      const randSize = makeLabLogoExploder.explodeSize
        ? Math.random() * (endStateSize * 2.5) + endStateSize / 2
        : endStateSize;
      startX           = Math.random() * (logicalWidth  - randSize * 2) + randSize;
      startY           = Math.random() * (logicalHeight - randSize * 2) + randSize;
      startFill        = START_FILL_COLOR;
      startStroke      = animTri.strokeColor;
      startSize        = randSize;
      startAngle       = Math.random() * 540;
      startStrokeWidth = animTri.strokeWidth;
    }

    // Apply the start state to the animated triangle
    animTri.x           = startX;
    animTri.y           = startY;
    animTri.fillColor   = startFill;
    animTri.strokeColor = startStroke;
    animTri.size        = startSize;
    animTri.angle       = startAngle;
    animTri.strokeWidth = startStrokeWidth;

    makeLabLogoExploder.originalRandomTriLocs.push({
      x:           startX,
      y:           startY,
      fillColor:   startFill,
      strokeColor: startStroke,
      size:        startSize,
      angle:       startAngle,
      strokeWidth: startStrokeWidth,
    });
  }
}

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
  // Holiday art re-fetches are not repeated — we reuse the same art positions
  // for subsequent resets to avoid async overhead on scroll.
  if (lerpAmount >= 1) {
    if (shouldResetOnFullExplosion) {
      if (holidayArtURL) {
        initWithHolidayArt(holidayArtURL);
      } else {
        makeLabLogoExploder.reset(logicalWidth, logicalHeight);
      }
      shouldResetOnFullExplosion = false;
    }
  } else {
    shouldResetOnFullExplosion = true;
  }
}

// =============================================================================
// Responsive Resizing
// =============================================================================

const parentDiv = document.querySelector('.col-md-6.center-canvas');

const resizeObserver = new ResizeObserver(entries => {
  const parentDivRect = entries[0].contentRect;

  const newLogicalWidth  = parentDivRect.width;
  const newLogicalHeight = Math.min(parentDivRect.height, MAX_HEIGHT);

  makeLabLogoExploder.fitToCanvas(newLogicalWidth, newLogicalHeight);

  logicalWidth  = newLogicalWidth;
  logicalHeight = newLogicalHeight;

  setCanvasSize(logicalWidth, logicalHeight);
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
 * @param {number} width  - Logical width in CSS pixels
 * @param {number} height - Logical height in CSS pixels
 */
function setCanvasSize(width, height) {
  canvas.style.width  = width  + 'px';
  canvas.style.height = height + 'px';
  canvas.width  = width  * DPR;
  canvas.height = height * DPR;
  ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
}

/**
 * Clears the canvas and draws the current state of the logo exploder.
 *
 * @param {CanvasRenderingContext2D} ctx
 */
function draw(ctx) {
  ctx.fillStyle = BG_FILL_COLOR;
  ctx.fillRect(0, 0, logicalWidth, logicalHeight);
  makeLabLogoExploder.draw(ctx);

  // Uncomment for debugging:
  // drawDebugOverlay(ctx);
}

/**
 * Draws debug information overlay showing canvas and logo dimensions.
 *
 * @param {CanvasRenderingContext2D} ctx
 */
function drawDebugOverlay(ctx) {
  const parentDivRect = parentDiv.getBoundingClientRect();

  ctx.fillStyle = 'black';
  ctx.font = '16px Arial';
  ctx.textAlign = 'center';

  const logoText = `Logo: ${makeLabLogoExploder.finalWidth.toFixed(1)} × ${makeLabLogoExploder.finalHeight.toFixed(1)}`;
  ctx.fillText(logoText, logicalWidth / 2, logicalHeight - 20);

  ctx.textBaseline = 'top';
  const canvasText = `Canvas: ${logicalWidth} × ${logicalHeight} (DPR: ${DPR}) | Parent: ${parentDivRect.width.toFixed(0)} × ${parentDivRect.height.toFixed(0)}`;
  ctx.fillText(canvasText, logicalWidth / 2, 4);
}