/**
 * Sets up the logo animation on the canvas element with the ID 'makelab-logo-canvas'.
 * Initializes the MakeabilityLabLogoExploder and handles the scroll event to update the animation.
 * 
 * @file /Users/jonfroehlich/Git/makeabilitylabwebsite/website/static/website/js/makelab-logo.js
 * @module makelab-logo
 */

import { MakeabilityLabLogoExploder, MakeabilityLabLogo} from 'https://cdn.jsdelivr.net/gh/makeabilitylab/js@main/dist/makelab.logo.js';

// Set up the logo animation
let canvas = document.getElementById('makelab-logo-canvas');
canvas.width = 500;
canvas.height = 300;
let triangleSize = 70;
let ctx = canvas.getContext('2d');

let bgFillColor = "white";
let startFillColor = "rgba(255, 255, 255, 0.5)";
let xPos = canvas.width/2 - MakeabilityLabLogo.getWidth(triangleSize) / 2;
let makeLabLogoExploder = new MakeabilityLabLogoExploder(xPos, 10, triangleSize, startFillColor);
makeLabLogoExploder.reset(canvas.width, canvas.height);
makeLabLogoExploder.draw(ctx);
let resetAnimationParams = false;

window.addEventListener('scroll', scrollHandler, { passive: true });

 /**
  * Handles the scroll event to update the MakeabilityLabLogoExploder animation.
  * 
  * @function scrollHandler
  */
function scrollHandler() {
  const scrollY = window.scrollY;
  const lerpAmt = Math.min(scrollY / 100, 1); // Adjust the 100 as needed

  makeLabLogoExploder.update(lerpAmt);
  draw(ctx);

  //console.log(`Scroll: ${scrollY}, Lerp: ${lerpAmt}, resetAnimationParams: ${resetAnimationParams}`);

  // Reset the animation parameters if lerpAmt reaches 1
  // But don't keep resetting unnecessarily
  if(lerpAmt >= 1){
    if(resetAnimationParams){
      makeLabLogoExploder.reset(canvas.width, canvas.height);
      resetAnimationParams = false;
    } 
  }else if(lerpAmt < 1){
    resetAnimationParams = true;
  }
}

 /**
  * Draws the MakeabilityLabLogoExploder on the provided canvas context.
  * Clears the canvas before drawing.
  * 
  * @function draw
  * @param {CanvasRenderingContext2D} ctx - The canvas rendering context to draw on.
  */
function draw(ctx){
  // clear canvas
  ctx.fillStyle = bgFillColor;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  makeLabLogoExploder.draw(ctx);
}