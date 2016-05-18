// Reusable sidebar module
//
// usage: $('#fixed-side-bar').fixedSideBar()
//
// Should also call $('#fixed-side-bar').resizeSideBar() when either the sidebar or main
// content changes, to avoid display issues when the sidebar is longer than the content
//
// Note: Depends on document elements with the ids "content" and "mainContent"
// 		#content should contain all content including the sidebar
// 		#mainContent should contain all other content (without the sidebar)

(function($) {
	var top = 0, initOffset = 0;
	var sideBar;

	$.fn.fixedSideBar = function() {

		// save a reference to "this" so that we can refer to it in the event handlers below
		sideBar = this;

		// save the current position of the filter bar to use when scrolling
		top = this.offset().top - parseInt(this.css('margin-top'));
		initOffset = this.css('top');

		// when the window scrolls, need to adjust the position of the filter bar
		$(window).scroll(function(event) {
			// check the vertical position of the scroll
		    var y = $(this).scrollTop();

		    // is it below the form?
		    if (y >= top) {
		        // if so, set fixed position
		        sideBar.css('position', 'fixed');
		        sideBar.css('top', '0');
		        sideBar.css('left', parseInt($('#content').css('margin-left')) + "px");
		    } else {
		        // otherwise set absolute position
		        sideBar.css('position', 'absolute');
		        sideBar.css('top', initOffset);
		        sideBar.css('left', "0");
		    }
		});

		// when the window is resized, need to adjust the filter bar position and 
		// publication list height to avoid formatting issues
		$(window).resize(function(event) {
			var minHeight = sideBar.height() + 10; // should probably use something from the css rather than a magic number here
			var content = $('#main-content');
			content.css('min-height', minHeight + "px");

			if(sideBar.css('position') == "fixed") {
				sideBar.css('left', parseInt($('#content').css('margin-left')) + "px");
			} else {
				sideBar.css('left', 0);
			}
		});

		return this;
	};

	$.fn.resizeSideBar = function() {
		var minHeight = this.height() + 10; // should probably use something from the css rather than a magic number here
		var content = $('#main-content');
		content.css('min-height', minHeight + "px");

		if(this.css('position') == "fixed") {
			this.css('left', parseInt($('#content').css('margin-left')) + "px");
		} else {
			this.css('left', 0);
		}

		return this;
	};
}(jQuery));