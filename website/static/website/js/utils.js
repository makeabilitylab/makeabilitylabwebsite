function heightFix(className) {
	var maxActive=0;
    $(className).each(function(index){
		if ($(this).height()>maxActive)
		    maxActive = $(this).height();
	    });
    $(className).each(function(index){
		$(this).height(maxActive);
	});
}