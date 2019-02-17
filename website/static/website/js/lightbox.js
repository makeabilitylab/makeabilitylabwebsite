"use strict";
(function(){

    window.onload = function(){
        let galleryImages = document.querySelectorAll(".project-gallery-col");
        for (let i = 0; i < galleryImages.length; i++) {
            galleryImages[i].onclick = function() {
                openLightBox();
            };
        }
        document.querySelector(".js-close-btn").onclick = closeLightBox;

    };

    /**
     * C
     */
    function openLightBox() {
        alert("open");
    }

    /**
     * E
     */
    function closeLightBox() {
        alert("close")
    }
})();