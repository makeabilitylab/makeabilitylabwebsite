// Reusable citation popover module used by display_pub_snippet.html
//
// usage: $(citationLink).citationPopover()
(function ($) {

    $.fn.citationPopover = function () {

        // Hide popovers when clicking outside, but not when clicking inside
        // from: http://stackoverflow.com/a/14857326
        // LS: this is a bit of a hack, since the default click behavior leaves them open
        // until you click on the button again, but the default focus behavior prevents you
        // from interacting with the content of the popover
        $('body').on('click', function (e) {
            $('[data-toggle="popover"]').each(function () {
                //the 'is' for buttons that trigger popups
                //the 'has' for icons within a button that triggers a popup
                if (!$(this).is(e.target) && $(this).has(e.target).length === 0 && $('.popover').has(e.target).length === 0) {
                    $(this).popover('hide');
                }
            });
        });

        $(this).updateCitationPopover();
        console.log("WE ARE HERE!");

        return this;
    }

    $.fn.citationclick = function () {
        console.log("citation click")
        $(".citation-text").css('display', 'block');
        $(".bibtex-text").css('display', 'none');
    }

    $.fn.bibtexclick = function () {
        $(".bibtex-text").css('display', 'block');
        $(".citation-text").css('display', 'none');
    }

    $.fn.updateCitationPopover = function () {
        $(this).popover({placement: "auto right"})

        // Manual trigger to get around idiosyncrasies of bootstrap's popover control
        $(this).click(function () {

            // prevent multiple popovers from being open at once
            var popovers = $('[data-toggle="popover"]')
            for (var i = 0; i < popovers.length; i++) {
                if (popovers[i] != this) // ignore the current popover
                    $(popovers[i]).popover('hide');
            }

            // toggle this popover
            $(this).popover('toggle');
        });
    }

}(jQuery));