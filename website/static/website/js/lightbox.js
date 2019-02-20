"use strict";
(function(){
    let slideIndex = 1;

    window.onload = function(){
        let galleryImages = document.querySelectorAll(".project-gallery-col");
        let lightboxImages = document.querySelectorAll(".myslides");
        console.log(slideIndex)
        for (let i = 0; i < galleryImages.length; i++) {
            galleryImages[i].onclick = function() {
                slideIndex = galleryImages[i].id.split(/([0-9]+)/)[1];//find a better solution
                console.log(slideIndex)
                openLightBox(galleryImages[i].id, lightboxImages);
            };
        }

        document.querySelector(".prev").onclick = function() {
            plusSlides(-1, lightboxImages);
        };

        document.querySelector(".next").onclick = function() {
            plusSlides(1, lightboxImages);
        };


        document.querySelector(".js-lightbox-close-btn").onclick = function() {
            closeLightBox(lightboxImages);
        };
    };

    /**
     * C
     */
    function openLightBox(slide, lightboxImages) {
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
    function closeLightBox(lightboxImages) {
        document.querySelector(".lightbox").classList.add("is-hidden");
        for (let i = 0; i < lightboxImages.length; i++) {
            lightboxImages[i].classList.remove("is-hidden");
        }
    }

    function plusSlides(n, lightboxImages) {
        slideIndex = Number(n) + Number(slideIndex);// find better solution
        if (slideIndex > lightboxImages.length) {
            slideIndex = 1;
        } else if (slideIndex < 1) {
            slideIndex = lightboxImages.length;
        }
        openLightBox("slide" + slideIndex, lightboxImages);
    }
})();