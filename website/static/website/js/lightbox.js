//  Handles the basic functions of the lightbox for image gallery. User can click on an image in the image gallery
//  to view it in a higher resolution. Once the lightbox is opened, the user change between the other photos in the
//  gallery by clicking the arrows. Bellow each image in the lightbox is its assigned caption.

"use strict";
(function(){
    let slideIndex; //Keeps track of the current slide number
    let lightboxImages; //Array of all the slides for the lightbox

    window.onload = function(){
        let galleryImages = document.querySelectorAll(".project-gallery-col");
        lightboxImages = document.querySelectorAll(".lightbox-slides");
        slideIndex = 1;

        for (let i = 0; i < galleryImages.length; i++) {
            galleryImages[i].onclick = function() {
                slideIndex = galleryImages[i].id.split(/([0-9]+)/)[1];
                openLightBox(galleryImages[i].id);
            };
        }

        document.querySelector(".prev").onclick = function() {
            slideChange(-1);
        };

        document.querySelector(".next").onclick = function() {
            slideChange(1);
        };

        document.querySelector(".lightbox-close-btn").onclick = closeLightBox;
    };

    /**
     * Opens the lightbox to the image clicked on and disables scrolling
     * @param {object} slide - id of the slide containing the image clicked on
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
        document.querySelector("body").classList.add("is-stop-scrolling");
    }

    /**
     * Closes the lightbox and re-enables scrolling
     */
    function closeLightBox() {
        document.querySelector(".lightbox").classList.add("is-hidden");
        for (let i = 0; i < lightboxImages.length; i++) {
            lightboxImages[i].classList.remove("is-hidden");
        }
        document.querySelector("body").classList.remove("is-stop-scrolling");
    }

    /**
     * Changes the slide to the next or previous slide
     * @param {int} slideNumber - Either '1' indicating the next slide or '-1' for the previous slide
     */
    function slideChange(slideNumber) {
        slideIndex = Number(slideNumber) + Number(slideIndex);
        if (slideIndex > lightboxImages.length) {
            slideIndex = 1;
        } else if (slideIndex < 1) {
            slideIndex = lightboxImages.length;
        }
        openLightBox("slide" + slideIndex, lightboxImages);
    }
})();