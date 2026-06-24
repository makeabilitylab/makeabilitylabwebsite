/**
 * Footer Logo Easter Egg (#1397)
 *
 * Progressive enhancement: replaces the static footer Makeability Lab logo
 * <img> with an interactive <canvas> driven by the makeabilitylab/js library
 * (the same lib that powers the landing-page logo and the 404 leaf-fall).
 *
 * Interaction:
 *   - Desktop (hover-capable, fine pointer): moving the cursor across the logo
 *     maps horizontal position to the morph amount along a linear "reverse
 *     explosion" path — left edge = fully exploded, right edge = fully
 *     assembled. On mouse-leave the logo eases back to assembled.
 *   - Touch (no hover / coarse pointer): a single tap plays a one-shot
 *     explode -> reassemble animation. (Finger-tracking horizontally would
 *     fight page scroll near the footer, so we use a tap instead.) The tap is
 *     consumed by the easter egg, so on touch the footer logo does NOT also
 *     navigate home — the navbar logo and footer links still do.
 *
 * Accessibility:
 *   - Honors prefers-reduced-motion: when set (or when canvas is unsupported),
 *     we leave the static <img> in place — no canvas, no animation.
 *   - The injected canvas carries role="img" + aria-label so its accessible
 *     name matches the logo it replaces.
 *
 * The library is pinned to a released tag (@0.6.0), not @main, so the easter
 * egg can't break when the library's bleeding edge changes.
 *
 * CDN cache can be purged at https://www.jsdelivr.com/tools/purge
 *
 * @author Jon Froehlich (with Claude Code)
 */

import {
  MakeabilityLabLogo,
  MakeabilityLabLogoMorpher,
  linearPath,
} from 'https://cdn.jsdelivr.net/gh/makeabilitylab/js@0.6.0/dist/makelab.logo.js';

// =============================================================================
// Configuration
// =============================================================================

const DPR = window.devicePixelRatio || 1;
// Logical triangle size before the logo is scaled to fit the canvas width.
const TRIANGLE_SIZE = 70;
// Keep the assembled logo within this fraction of the canvas width so the
// exploded triangles still have room to scatter without clipping.
const LOGO_WIDTH_FRACTION = 0.9;
// Extra vertical breathing room (logical px) added above/below the logo.
const VERTICAL_PADDING = 6;
// The logo renders white-on-dark to match the footer's white wordmark PNG.
const LOGO_COLOR = 'white';
// Faint white for the exploded (scattered) triangles before they assemble.
const START_FILL_COLOR = 'rgba(255, 255, 255, 0.35)';
// Fraction of the canvas width treated as dead margin on each side, so the
// fully-exploded / fully-assembled states are reachable before the very edge.
const EDGE_MARGIN_FRACTION = 0.08;
// One-shot tap animation timings (ms).
const TAP_EXPLODE_MS = 450;
const TAP_ASSEMBLE_MS = 750;
// Ease-back-to-assembled duration when the cursor leaves (ms).
const LEAVE_MS = 500;

// =============================================================================
// Easing
// =============================================================================

const easeOutCubic = (t) => 1 - Math.pow(1 - t, 3);
const easeInOutCubic = (t) =>
  t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
const clamp = (v, lo, hi) => Math.min(Math.max(v, lo), hi);

// =============================================================================
// Reduced motion (#1294)
// =============================================================================

function prefersReducedMotion() {
  if (window.MakeLab && window.MakeLab.prefersReducedMotion) {
    return window.MakeLab.prefersReducedMotion();
  }
  return !!(
    window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  );
}

// =============================================================================
// State
// =============================================================================

let canvas = null;
let ctx = null;
let link = null;
let morpher = null;
let logicalWidth = 0;
let logicalHeight = 0;
let lastCssWidth = -1;
// 1 = fully assembled (the resting state); 0 = fully exploded.
let currentLerp = 1;
let rafId = null;

// =============================================================================
// Rendering
// =============================================================================

/**
 * Applies the white-on-dark color scheme. The M/L outlines and the wordmark
 * label are drawn from dedicated properties (not setColors), and the morpher
 * keeps two logo instances (the hidden target + the animated one), so we whiten
 * every channel on both to get a clean all-white logo on the blue footer.
 */
function applyColors() {
  for (const logo of [morpher.makeLabLogo, morpher.makeLabLogoAnimated]) {
    logo.setColors(LOGO_COLOR, LOGO_COLOR);
    logo.mOutlineColor = LOGO_COLOR;
    logo.lOutlineColor = LOGO_COLOR;
    logo.setLTriangleStrokeColor(LOGO_COLOR);
    logo.labelColor = LOGO_COLOR;
  }
}

function render() {
  if (!morpher) return;
  // Clear to transparent so the footer's dark background shows through.
  ctx.clearRect(0, 0, logicalWidth, logicalHeight);
  morpher.update(currentLerp);
  morpher.draw(ctx);
}

/**
 * (Re)sizes the canvas to its CSS box and lays out the logo within it.
 * Guarded so the ResizeObserver (which also fires when we set the height)
 * only does real work when the canvas *width* actually changes.
 * @param {boolean} force - relayout even if the width is unchanged.
 */
function layout(force) {
  const cssWidth = Math.round(
    canvas.clientWidth || canvas.getBoundingClientRect().width || 160
  );
  if (!force && cssWidth === lastCssWidth) return;
  lastCssWidth = cssWidth;

  // Scale the assembled logo to fit the canvas width (capped at natural size).
  const naturalLogoWidth = MakeabilityLabLogo.numCols * TRIANGLE_SIZE;
  const targetLogoWidth = Math.min(naturalLogoWidth, cssWidth * LOGO_WIDTH_FRACTION);
  morpher.setLogoSize(targetLogoWidth);

  // makeLabLogo.height already accounts for the wordmark label below the logo.
  const cssHeight = Math.ceil(morpher.makeLabLogo.height + VERTICAL_PADDING * 2);
  logicalWidth = cssWidth;
  logicalHeight = cssHeight;

  canvas.style.height = cssHeight + 'px';
  canvas.width = cssWidth * DPR;
  canvas.height = cssHeight * DPR;
  ctx.setTransform(DPR, 0, 0, DPR, 0, 0);

  morpher.centerLogo(logicalWidth, logicalHeight);
  morpher.reset(logicalWidth, logicalHeight);
  applyColors(); // reset() can repopulate triangle colors; reassert ours.
  render();
}

// =============================================================================
// Animation helpers
// =============================================================================

function cancelTween() {
  if (rafId) {
    cancelAnimationFrame(rafId);
    rafId = null;
  }
}

/**
 * Tweens currentLerp to `target` over `duration` ms using `easing`, then calls
 * `onDone`. Uses the rAF timestamp for timing (no Date.now()).
 */
function tweenTo(target, duration, easing, onDone) {
  cancelTween();
  const startLerp = currentLerp;
  const delta = target - startLerp;
  let startTs = null;
  function step(ts) {
    if (startTs === null) startTs = ts;
    const t = duration > 0 ? Math.min((ts - startTs) / duration, 1) : 1;
    currentLerp = startLerp + delta * easing(t);
    render();
    if (t < 1) {
      rafId = requestAnimationFrame(step);
    } else {
      rafId = null;
      if (onDone) onDone();
    }
  }
  rafId = requestAnimationFrame(step);
}

// =============================================================================
// Interaction handlers
// =============================================================================

// Desktop: track the cursor's X position across the logo.
function onPointerEnter() {
  // Re-scatter so each hover gets a fresh explosion pattern.
  if (morpher) morpher.reset(logicalWidth, logicalHeight);
}

function onPointerMove(e) {
  cancelTween();
  const rect = canvas.getBoundingClientRect();
  const margin = rect.width * EDGE_MARGIN_FRACTION;
  const usable = rect.width - 2 * margin;
  const x = e.clientX - rect.left;
  // Left edge -> 0 (exploded); right edge -> 1 (assembled).
  currentLerp = usable > 0 ? clamp((x - margin) / usable, 0, 1) : 1;
  render();
}

function onPointerLeave() {
  tweenTo(1, LEAVE_MS, easeOutCubic);
}

// Touch: tap plays a one-shot explode -> reassemble.
function onTap(e) {
  // The easter egg owns this tap; don't also navigate home.
  e.preventDefault();
  if (rafId) return; // ignore taps mid-animation
  morpher.reset(logicalWidth, logicalHeight);
  tweenTo(0, TAP_EXPLODE_MS, easeOutCubic, () =>
    tweenTo(1, TAP_ASSEMBLE_MS, easeInOutCubic)
  );
}

// =============================================================================
// Setup
// =============================================================================

function enhance(img) {
  link = img.closest('a');
  if (!link) return;

  canvas = document.createElement('canvas');
  // Reuse the img's sizing class so the canvas inherits the same responsive
  // max-width (incl. the #1395 mobile shrink) and centering.
  canvas.className = 'makelab-footer-logo makelab-footer-logo-canvas';
  canvas.setAttribute('role', 'img');
  canvas.setAttribute('aria-label', 'Makeability Lab');
  ctx = canvas.getContext('2d');
  if (!ctx) return; // no 2D context -> keep the static img

  img.insertAdjacentElement('afterend', canvas);
  img.style.display = 'none';

  morpher = new MakeabilityLabLogoMorpher(0, 0, TRIANGLE_SIZE, START_FILL_COLOR);
  morpher.setPath(linearPath()); // explicit linear "reverse explosion" trajectory
  applyColors();
  layout(true);

  const canHover = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
  if (canHover) {
    // Hover drives the morph; a normal click still navigates home.
    canvas.addEventListener('pointerenter', onPointerEnter);
    canvas.addEventListener('pointermove', onPointerMove);
    canvas.addEventListener('pointerleave', onPointerLeave);
  } else {
    // Touch: tap plays the animation (and suppresses navigation).
    link.addEventListener('click', onTap);
  }

  new ResizeObserver(() => layout(false)).observe(canvas);
}

const footerImg = document.getElementById('makelab-footer-logo-img');
if (
  footerImg &&
  !prefersReducedMotion() &&
  !!document.createElement('canvas').getContext
) {
  enhance(footerImg);
}
