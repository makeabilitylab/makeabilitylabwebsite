// auto-hide button scroll to top: http://webdesignerwall.com/demo/scroll-to-top/scrolltotop.html
// provide the back to top button
// hide #back-top first
$(document).ready(function(){
    var offset = 300; // The amount of scrolling before the button appears
    var duration = 100; // The time of the fade in
    $(window).scroll(function() {
    	// console.log("$(this).scrollTop():" + $(this).scrollTop() + " offset: " + offset)

		if ($(this).scrollTop() > offset) {
    		// console.log("Showing scroll top button!!!")
			$('#back-top').fadeIn(duration);
		}
		else {
    		// console.log("Hiding scroll top button")
			$('#back-top').fadeOut(duration);
		}
    });

    // scroll body to 0px on click
    $('#back-top a').click(function () {
        $('body,html').animate({
            scrollTop: 0
        }, 800);
        return false;
    });
});
