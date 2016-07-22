$(document).ready(function(){
    var offset = 300; // The amount of scrolling before the button appears
    var duration = 100; // The time of the fade in
    $(window).scroll(function() {
	if ($(this).scrollTop() > offset) {
	    $('#back-top').fadeIn(duration);
	}
	else {
	    $('#back-top').fadeOut(duration);
	}
    });
});
