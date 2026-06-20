/**
 * Makeability Lab 404 Animation — Leaf Fall (#1190)
 *
 * The page loads fully assembled: a full-window grid of colored triangles with
 * the Makeability Lab logo embedded. After a short beat it "breaks" — the
 * background grid triangles flutter down like falling leaves and pile at the
 * bottom, leaving the logo standing intact. (Per the library, dropLeaves() drops
 * only the background grid; the logo's own pieces stay fixed.)
 *
 * Uses MakeabilityLabLogoLeafFall from the pinned CDN dist (makeabilitylab/js
 * 0.5.0). Click anywhere or press R to replay. Honors prefers-reduced-motion by
 * rendering just the static logo (grid hidden), no animation.
 *
 * Recovery content (heading, links) lives in the DOM, not here.
 *
 * Requires <canvas id="makelab-404-canvas"> inside a sized parent (.error-page).
 *
 * @author Makeability Lab
 */

import {
  MakeabilityLabLogo,
  MakeabilityLabLogoLeafFall,
} from 'https://cdn.jsdelivr.net/gh/makeabilitylab/js@0.6.0/dist/makelab.logo.js';

// =============================================================================
// Configuration
// =============================================================================

const TRIANGLE_SIZE = 70;
// Logo size also sets the grid cell size (the grid is built from the logo's
// triangle size), so shrinking the logo makes the whole grid finer too.
const LOGO_WIDTH_FRACTION = 0.48;
const LOGO_MAX_WIDTH = 320;
const DPR = window.devicePixelRatio || 1;

// How long the assembled logo holds before the leaves drop.
const DROP_DELAY_MS = 1500;
// Drop animation length (groundStagger 700 + groundFallMax 1700 + buffer); the
// loop stops after this so we don't spin the CPU once everything has settled.
const DROP_ANIM_MS = 2900;

// =============================================================================
// Setup
// =============================================================================

const canvas = document.getElementById('makelab-404-canvas');
const ctx = canvas.getContext('2d');
const stage = canvas.parentElement; // the sized .error-page section

function prefersReducedMotion() {
  if (window.MakeLab && window.MakeLab.prefersReducedMotion) {
    return window.MakeLab.prefersReducedMotion();
  }
  return !!(window.matchMedia &&
            window.matchMedia('(prefers-reduced-motion: reduce)').matches);
}

const reducedMotion = prefersReducedMotion();
if (reducedMotion) {
  canvas.setAttribute('aria-label', 'Makeability Lab logo');
}

let logicalWidth = 0;
let logicalHeight = 0;
let logo = null;
let leafFall = null;
let isReady = false;
let startTime = null;   // rAF timestamp when the current cycle began
let dropped = false;    // whether dropLeaves() has fired this cycle
let running = false;    // whether the rAF loop is active

// =============================================================================
// Layout
// =============================================================================

function sizeCanvas() {
  const rect = stage.getBoundingClientRect();
  logicalWidth = Math.max(rect.width, 1);
  logicalHeight = Math.max(rect.height, 1);

  canvas.width = logicalWidth * DPR;
  canvas.height = logicalHeight * DPR;
  ctx.setTransform(DPR, 0, 0, DPR, 0, 0);

  // (Re)build the logo + leaf-fall for the current size. The grid fills the
  // canvas, aligned to the centered logo.
  logo = new MakeabilityLabLogo(0, 0, TRIANGLE_SIZE);
  const naturalWidth = MakeabilityLabLogo.numCols * TRIANGLE_SIZE;
  const maxWidth = Math.min(LOGO_MAX_WIDTH, logicalWidth * LOGO_WIDTH_FRACTION);
  logo.setLogoSize(Math.min(naturalWidth, maxWidth));
  // Bias the logo slightly below center so it clears the heading above it.
  logo.centerLogo(logicalWidth, logicalHeight * 1.08);
  // Nudge the logo up by some grid cells. On tall, narrow (mobile) viewports the
  // centered logo sits too low, so lift it more there. Use a CONTINUOUS ramp
  // (not a hard breakpoint) so there's no jarring jump near 768px: 1 cell on
  // desktop, smoothly increasing to ~3 cells as the width shrinks to ~360px.
  // (cellSize scales with the logo, so this stays in grid-cell units.) Done
  // before building the leaf-fall so its grid aligns to this final position and
  // the reveal stays seamless.
  const narrowness = Math.max(0, Math.min(1, (768 - logicalWidth) / (768 - 360)));
  const cellsUp = 1 + narrowness * 2;
  logo.setLogoPosition(logo.x, logo.y - cellsUp * logo.cellSize);

  // Make the "L" overlay semi-translucent so it reads as a subtle sheen and lets
  // the colored logo show through (setLTriangleFillColor added in js 0.6.0).
  logo.setLTriangleFillColor('rgba(255, 255, 255, 0.5)');

  leafFall = new MakeabilityLabLogoLeafFall(logo, logicalWidth, logicalHeight, {
    startAssembled: true,
  });

  isReady = true;

  if (reducedMotion) {
    // Static: jump straight to the settled end state (leaves already piled,
    // colored logo intact) with no animation. We can't just hide the grid --
    // the logo's colors ARE pinned grid cells, so hiding it would leave only
    // the black outline.
    leafFall.dropLeaves();
    leafFall.update(0);                    // captures the drop start clock
    leafFall.update(DROP_ANIM_MS + 1000);  // fast-forward to the settled pile
    render();
  } else {
    start();
  }
}

// =============================================================================
// Rendering
// =============================================================================

function render() {
  if (!isReady) return;
  ctx.clearRect(0, 0, logicalWidth, logicalHeight);
  leafFall.draw(ctx);
}

// =============================================================================
// Animation loop — hold assembled, drop leaves, then settle and stop.
// =============================================================================

function frame(now) {
  if (startTime === null) startTime = now;
  const elapsed = now - startTime;

  if (!dropped && elapsed >= DROP_DELAY_MS) {
    leafFall.dropLeaves();
    dropped = true;
  }

  leafFall.update(elapsed);
  render();

  if (elapsed < DROP_DELAY_MS + DROP_ANIM_MS) {
    requestAnimationFrame(frame);
  } else {
    running = false; // settled; stop spinning the CPU
  }
}

function start() {
  if (reducedMotion || !leafFall) return;
  leafFall.reset();
  startTime = null;
  dropped = false;
  if (!running) {
    running = true;
    requestAnimationFrame(frame);
  }
}

// =============================================================================
// Kick-off
// =============================================================================

const resizeObserver = new ResizeObserver(() => sizeCanvas());
resizeObserver.observe(stage);
sizeCanvas();

if (!reducedMotion) {
  // Replay on click or the "R" key.
  window.addEventListener('click', start);
  window.addEventListener('keydown', (e) => { if (e.key === 'r' || e.key === 'R') start(); });
}
