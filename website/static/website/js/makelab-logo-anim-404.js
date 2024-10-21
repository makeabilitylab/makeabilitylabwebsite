import { MakeabilityLabLogoExploder, MakeabilityLabLogo} from 'https://cdn.jsdelivr.net/gh/makeabilitylab/js@main/dist/makelab.logo.js';

// Set up the logo animation
let canvas = document.getElementById('makelab-logo-canvas');
const MAX_HEIGHT = 300;
canvas.width = 500;
canvas.height = MAX_HEIGHT;
let triangleSize = 70;
let ctx = canvas.getContext('2d');

let bgFillColor = "rgba(255, 255, 255, 0.2)";
//let bgFillColor = "rgba(255, 0, 0, 1)";
let startFillColor = "rgba(255, 255, 255, 0.5)";
let xPos = canvas.width/2 - MakeabilityLabLogo.getWidth(triangleSize) / 2;
let makeLabLogoExploder = new MakeabilityLabLogoExploder(xPos, 10, triangleSize, startFillColor);
makeLabLogoExploder.reset(canvas.width, canvas.height);
makeLabLogoExploder.update(1);
makeLabLogoExploder.draw(ctx);
let resetAnimationParams = false;

// Enable anti-aliasing
ctx.imageSmoothingEnabled = true;

draw(ctx);

document.addEventListener('mousemove', function(event) {
  const x = event.clientX;
  const y = event.clientY;
  // const windowWidth = window.innerWidth * 0.8;
  // const lerpAmt = Math.min(x / windowWidth, 1);

  // We're going to animate the logo explosion based on the mouse position
  // If it's in the middle of the window, the logo will be fully together (lerpAmt = 1)
  // If it's to the left or right edge, the logo will be fully exploded (lerpAmt = 0)
  // if the mouse is in the center of the screen and within the buffer, the logo is fully together
  const middleBuffer = 50; 
  const leftEdge = window.innerWidth / 2 - middleBuffer / 2;
  const rightEdge = window.innerWidth / 2 + middleBuffer / 2;
  let lerpAmt = 1;
  if (x < leftEdge || x > rightEdge) {
    const totalWidth = window.innerWidth / 2 - middleBuffer / 2;
    const distanceToEdge = x < leftEdge ? leftEdge - x : x - rightEdge;
    lerpAmt = 1 - distanceToEdge / totalWidth;
  }

  // Reset the animation parameters if lerpAmt reaches 1
  if(lerpAmt >= 1){
    if(resetAnimationParams){
      makeLabLogoExploder.reset(canvas.width, canvas.height);
      resetAnimationParams = false;
      // console.log("Resetting explosion positions");
    }     
  }else{
    resetAnimationParams = true;
  }
  
  document.getElementById('position').textContent = 'X: ' + x + ', Y: ' + y + ', Lerp: ' + lerpAmt;;
  makeLabLogoExploder.update(lerpAmt);
  draw(ctx);
  
});

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

  // Uncomment the following to debug
  // drawDebugText(ctx);
} 

/**
 * Draws debug text on the canvas, displaying the dimensions of the logo and the canvas.
 *
 * @param {CanvasRenderingContext2D} ctx - The 2D rendering context for the drawing surface of the canvas element.
 */
function drawDebugText(ctx){
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