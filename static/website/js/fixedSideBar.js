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
	var top = 0, initOffset = 0, bottom = 0, bottomOffset = 0;
	var sideBar;
	var alignedContainer = "";

	function offset(el) {
		var rect = el.getBoundingClientRect(),
		scrollLeft = window.pageXOffset || document.documentElement.scrollLeft,
		scrollTop = window.pageYOffset || document.documentElement.scrollTop;
		return { top: rect.top + scrollTop, left: rect.left + scrollLeft }
	}

	$.fn.setAlignedContainer = function(_containerToAlign){
		alignedContainer = _containerToAlign;
	};




	$.fn.fixedSideBar = function() {

		// save a reference to "this" so that we can refer to it in the event handlers below
		sideBar = this;

		// save the current position of the filter bar to use when scrolling
		top = this.offset().top - parseInt(this.css('margin-top'));
		initOffset = this.css('top');
		bottom = $(document).height();
		bottomOffset = $(document).height() - this.height() - parseInt(this.css('margin-top'));

		// when the window scrolls, need to adjust the position of the filter bar
		$(window).scroll(function(event) {
			 adjustScroll();
		});

		// when the window is resized, need to adjust the filter bar position and 
		// publication list height to avoid formatting issues
		$(window).resize(function(event) {
			adjustScroll();
			var minHeight = sideBar.height() + 10; // TODO: should probably use something from the css rather than a magic number here
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

	function adjustScroll(){
		if(alignedContainer !== "") {
				var container_height = $(alignedContainer)[0].scrollHeight;
                var container_top = offset($(alignedContainer)[0]).top;
                var sidebar_margin = parseInt(sideBar.css('margin-top'));
                var sidebar_height = sideBar.height();
                top = container_top - sidebar_margin;
                bottom = container_top + container_height - sidebar_height - sidebar_margin;
                bottomOffset = container_height - sidebar_height - sidebar_margin;
            }

			// check the vertical position of the scroll
		    var y = $(this).scrollTop();
		    var footer = $(".makelab-footer");

		    // is it below the form?
		    if (y >= top && y <= bottom) {
		        // if so, set fixed position
		        sideBar.css('position', 'fixed');
		        sideBar.css('top', "0");
		        sideBar.css('left', parseInt($('#content').css('margin-left')) + "px");
		    } else {
		        if (y <= top) {
		    		sideBar.css('position', 'absolute');
		    		sideBar.css ('top', initOffset);
		    		sideBar.css('left', 0);
		    	}
		    }
	}

	$.fn.resizeSideBar = function() {
		var minHeight = this.height() + 10; // TODO: should probably use something from the css rather than a magic number here
		var content = $('#content');
		content.css('min-height', minHeight + "px");

		if(this.css('position') == "fixed") {
			this.css('left', parseInt($('#content').css('margin-left')) + "px");
		} else {
			this.css('left', 0);
		}

		return this;
	};
}(jQuery));