
var _swapImageEnabled = true;
console.log("Hi console friends 👋🏽,\n\nTo turn off our 'easter egg' swap, " +
            "in the console window, type 'toggleSwapImage(false)'.")

function swapImage(imgElement) {
  if (_swapImageEnabled) {
    let temp = imgElement.src;
    imgElement.src = imgElement.dataset.altSrc;
    imgElement.dataset.altSrc = temp;
  }
}

function toggleSwapImage(swapImageEnabled=null) {
  if (swapImageEnabled == null) {
    _swapImageEnabled = !_swapImageEnabled;
  }else{
    _swapImageEnabled = swapImageEnabled;
  }
  console.log("Swap image is now " + (_swapImageEnabled ? "enabled" : "disabled") + ".");
}
