$(window).load(function(){
    var maxActive=0;
    $('.people-col').each(function(index){
	if ($(this).height()>maxActive)
	    maxActive = $(this).height();
    });
    $('.people-col').each(function(index){
	$(this).height(maxActive);
    });
});
