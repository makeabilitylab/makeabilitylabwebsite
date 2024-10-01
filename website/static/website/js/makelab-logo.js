import { MakeabilityLabLogoExploder, MakeabilityLabLogo } from 'https://cdn.jsdelivr.net/gh/makeabilitylab/js@main/dist/makelab.logo.js';

// Set up the logo animation
let canvas = document.getElementById('makelab-logo-canvas');
canvas.width = 500;
canvas.height = 300;
let triangleSize = 70;
let ctx = canvas.getContext('2d');

// let logo = new MakeabilityLabLogo(50, 10, triangleSize);
// logo.draw(ctx);
// console.log('Logo drawn');

let startFillColor = "rgba(255, 255, 255, 0.5)";
let makeLabLogoExploder = new MakeabilityLabLogoExploder(50, 10, triangleSize, startFillColor);
makeLabLogoExploder.reset(canvas.width, canvas.height);
makeLabLogoExploder.draw(ctx);

window.addEventListener('scroll', scrollHandler);
printMenu();

function scrollHandler() {
  const scrollY = window.scrollY;
  const lerpAmt = Math.min(scrollY / 100, 1); // Adjust the 100 as needed

  makeLabLogoExploder.update(lerpAmt);
  draw(ctx);
}

function draw(ctx){
  // clear canvas
  ctx.fillStyle = 'white';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  makeLabLogoExploder.draw(ctx);
}