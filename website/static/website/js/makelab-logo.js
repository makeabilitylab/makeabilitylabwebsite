/**
 * Sets up the logo animation on the canvas element with the ID 'makelab-logo-canvas'.
 * Initializes the MakeabilityLabLogoExploder and handles the scroll event to update the animation.
 * 
 * You can purge the cache of the CDN by visiting the following URL:
 * https://www.jsdelivr.com/tools/purge
 * 
 * @file /Users/jonfroehlich/Git/makeabilitylabwebsite/website/static/website/js/makelab-logo.js
 * @module makelab-logo
 */

//import { MakeabilityLabLogoExploder, MakeabilityLabLogo} from 'https://cdn.jsdelivr.net/gh/makeabilitylab/js@main/dist/makelab.logo.js';
import { MakeabilityLabLogoExploder, MakeabilityLabLogo} from './makelab.all.js';

// Set up the logo animation
let canvas = document.getElementById('makelab-logo-canvas');
canvas.width = 500;
canvas.height = 300;
let triangleSize = 70;
let ctx = canvas.getContext('2d');

let bgFillColor = "rgba(255, 255, 255, 0.2)";
//let bgFillColor = "rgba(255, 0, 0, 1)";
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
  const lerpAmt = Math.min(scrollY / 150, 1); // Adjust the 100 as needed

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

console.log("Setting up ResizeObserver for parent div");
const parentDiv = document.querySelector('.col-md-6.center-canvas');

const resizeObserver = new ResizeObserver(entries => {
  
  const parentDivRect = entries[0].contentRect;
  console.log("Parent div dimensions changed! ", parentDivRect);

  const boundingClientRect = entries[0].target.getBoundingClientRect();
  console.log("Bounding client rect: ", boundingClientRect);
  // if (newWidth < 500) {
  //   // Handle the case where parent div is less than 500px wide
  //   console.log(`Parent div is less than 500px wide! It's ${newWidth}px wide.`);
  //   // You can potentially adjust the animation here
  //   //makeLabLogoExploder.reset(newWidth, canvas.height);
  //   const logoSize = Math.max(newWidth * 0.9, 200);
  //   console.log("New logo size:", logoSize);
  //   makeLabLogoExploder.setLogoSize(logoSize);
  //   canvas.width = newWidth;
  //   //makeLabLogoExploder.centerLogo(boundingClientRect.width, boundingClientRect.height);
  //   makeLabLogoExploder.centerLogo(newWidth, boundingClientRect.height);
  //   draw(ctx);
  // }

  
  // Handle the case where parent div is less than 500px wide
  console.log(`Parent div is ${parentDivRect.width}px wide.`);
  // You can potentially adjust the animation here
  //makeLabLogoExploder.reset(newWidth, canvas.height);
  const maxLogoWidth = Math.min(parentDivRect.width, canvas.width);
  const maxLogoHeight = Math.min(parentDivRect.height, canvas.height);
  const maxLogoSize = Math.max(maxLogoWidth, maxLogoHeight);
  console.log(`maxLogoWidth: ${maxLogoWidth}, maxLogoHeight: ${maxLogoHeight}, maxLogoSize: ${maxLogoSize}`);
  const logoSize = maxLogoSize * 1;
  console.log("New logo size:", logoSize);
  //makeLabLogoExploder.setLogoSize(logoSize);
  makeLabLogoExploder.fitToCanvas(maxLogoWidth, maxLogoHeight);
  //makeLabLogoExploder.setLogoSize(500);
  canvas.width = parentDivRect.width;
  canvas.height = parentDivRect.height; //Math.max(300, parentDivRect.height);
  //makeLabLogoExploder.centerLogo(boundingClientRect.width, boundingClientRect.height);
  //makeLabLogoExploder.centerLogo(newWidth, boundingClientRect.height);
  //makeLabLogoExploder.setLogoPosition(0, 0);
  makeLabLogoExploder.centerLogo(parentDivRect.width, canvas.height);
  
  //TODO: we want to center the logo across x but not y

  draw(ctx);
  
});
resizeObserver.observe(parentDiv);

// console.log("Setting up ResizeObserver for parent div");
// const parentDiv = document.querySelector('.col-md-6.center-canvas');

// if (parentDiv) {
//   console.log("Parent div found:", parentDiv);

//   const resizeObserver = new ResizeObserver(entries => {
//     console.log("ResizeObserver callback triggered");
//     for (let entry of entries) {
//       console.log("Parent div width changed!");
//       const newWidth = entry.contentRect.width;
//       console.log("New width:", newWidth);
//       if (newWidth < 500) {
//         console.log("Parent div is less than 500px wide!");
//         // Handle the case where parent div is less than 500px wide
//         // You can potentially adjust the animation here
//       }
//     }
//   });

//   resizeObserver.observe(parentDiv);
// } else {
//   console.error("Parent div not found");
// }

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

  const parentDivDimensions = parentDiv.getBoundingClientRect();

  // set text properties
  ctx.fillStyle = 'black';
  ctx.font = '16px Arial';

  // show width and height of logo
  const logoDimensionsText = `Logo: ${makeLabLogoExploder.finalWidth.toFixed(1)} x ${makeLabLogoExploder.finalHeight.toFixed(1)}`;
  // console.log(logoDimensionsText);
  ctx.textAlign = 'center';
  const logoDimensionsTextMetrics = ctx.measureText(logoDimensionsText);
  ctx.fillText(logoDimensionsText, canvas.width / 2, canvas.height - 20);

  // measure and draw canvas.width centered at the top
  const marginText = 4;
  const widthText = "Canvas: " + canvas.width.toString() +
    " Parent div: " + parentDivDimensions.width;
  const widthTextMetrics = ctx.measureText(widthText);
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';
  ctx.fillText(widthText, canvas.width / 2, marginText);

  // measure and draw canvas.height rotated 90 degrees and centered vertically
  const heightText = "Canvas: " + canvas.height.toString() +
    " Parent div: " + parentDivDimensions.height.toFixed(1);
  const heightTextMetrics = ctx.measureText(heightText);
  ctx.save();
  ctx.translate(0, canvas.height / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';
  ctx.fillText(heightText, 0, marginText);
  ctx.restore();
}