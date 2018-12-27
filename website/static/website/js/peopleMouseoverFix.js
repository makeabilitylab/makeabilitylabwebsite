// When user hovers over the name of a person on the people page, it will show their easter egg image
$(document).ready(function(){
    $('.people-col .easter-egg-name').hover(function() {
            $(this).parents(".people-col").find('.easter-egg-col .main-image').addClass('easter-egg-hide');
            $(this).parents(".people-col").find('.overlay-easter-egg').addClass('easter-egg-show');
            }, function() {
            $(this).parents(".people-col").find('.easter-egg-col .main-image').removeClass('easter-egg-hide');
            $(this).parents(".people-col").find('.overlay-easter-egg').removeClass('easter-egg-show');
    });
});