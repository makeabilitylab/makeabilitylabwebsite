"use strict";
(function(){
    let slideIndex;
    let lightboxImages;

    window.onload = function(){
        let galleryImages = document.querySelectorAll(".project-gallery-col");
        lightboxImages = document.querySelectorAll(".lightbox-slides");
        slideIndex = 1;
        for (let i = 0; i < galleryImages.length; i++) {
            galleryImages[i].onclick = function() {
                slideIndex = galleryImages[i].id.split(/([0-9]+)/)[1];//find a better solution
                openLightBox(galleryImages[i].id);
            };
        }

        document.querySelector(".prev").onclick = function() {
            slideChange(-1);
        };

        document.querySelector(".next").onclick = function() {
            slideChange(1);
        };

        document.querySelector(".js-lightbox-close-btn").onclick = closeLightBox;
    };

    /**
     * C
     */
    function openLightBox(slide) {
        for (let i = 0; i < lightboxImages.length; i++) {
            if (lightboxImages[i].id !== "lightbox-" + slide) {
                lightboxImages[i].classList.add("is-hidden");
            } else {
                lightboxImages[i].classList.remove("is-hidden");
            }
        }
        document.querySelector(".lightbox").classList.remove("is-hidden");
    }

    /**
     * E
     */
    function closeLightBox() {
        document.querySelector(".lightbox").classList.add("is-hidden");
        for (let i = 0; i < lightboxImages.length; i++) {
            lightboxImages[i].classList.remove("is-hidden");
        }
    }

    /**
     * E
     */
    function slideChange(slideNumber) {
        slideIndex = Number(slideNumber) + Number(slideIndex);// find better solution
        if (slideIndex > lightboxImages.length) {
            slideIndex = 1;
        } else if (slideIndex < 1) {
            slideIndex = lightboxImages.length;
        }
        openLightBox("slide" + slideIndex, lightboxImages);
    }
})();