// https://forums.adobe.com/thread/786261
var savedRuler= app.preferences.rulerUnits;  
app.preferences.rulerUnits = Units.PIXELS;  
var w = app.activeDocument.width;  
var h = app.activeDocument.height;  
if(w>h) app.activeDocument.resizeCanvas (w, w, AnchorPosition.MIDDLECENTER);  
if(w<h) app.activeDocument.resizeCanvas (h, h, AnchorPosition.MIDDLECENTER);  
//if w==h already square  
app.preferences.rulerUnits = savedRuler;