
// When the page loads, all FAQs and responses will be shown and all topics in the menu bar will NOT be expanded. When
// the user clicks on a topic in the menu bar, it will expand and at the same time close any other topics that are open.
// If the user clicks the same topic again, the side panel menu will collapse, but stay on the same topic of questions.
// Page will automatically show and hide the FAQs and responses for a certain topic depending on if it is selected or not.

"use strict";
(function(){

    window.onload = function(){
        let panelTopics = document.querySelectorAll(".panel-grouping");
        for (let i = 0; i < panelTopics.length; i++) {
            panelTopics[i].querySelector(".topic").onclick = function() {
                let plusMinus = panelTopics[i].querySelector("span");
                let nameID = panelTopics[i].querySelector(".topic a").innerText.toLowerCase().split(" ").join("-");
                let openedTopic = (plusMinus && plusMinus.innerText !== "-" || nameID === "view-all-questions");
                closeAllPanelTopics(panelTopics, openedTopic);
                if (openedTopic) {
                    openSelectedTopic(panelTopics[i], plusMinus, nameID);
                }
            };
        }
    };

    /**
     * Closes all expanded panels in the menu bar and hides all FAQ's and responses.
     * @param {object} panelTopics - list of all the panel topics on FAQ page
     * @param {boolean} topicItemsActive - true/false if the side panel is already expanded
     */
    function closeAllPanelTopics(panelTopics, topicItemsActive) {
        for (let i = 0; i < panelTopics.length; i++) {
            let nameID = panelTopics[i].querySelector(".topic a").innerText.toLowerCase().split(" ").join("-");
            panelTopics[i].querySelector(".subtopics").classList.remove("subtopics-active");
            if (nameID !== "view-all-questions") {
                panelTopics[i].querySelector("span").innerText = "+";
                if (topicItemsActive) {
                    document.getElementById(nameID).classList.remove("topic-items-active");
                }
            }
        }
    }

    /**
     * Expands the chosen topic in the menu bar and shows the FAQ's and responses.
     * @param {object} topic - the selected menu bar topic
     * @param {element} plusMinus - the selected menu bar topic's plus/minus sign element.
     * @param {String} nameID - the id of FAQ topic selected
     */
    function openSelectedTopic(topic, plusMinus, nameID) {
        if (nameID === "view-all-questions") {
            let questions = document.querySelectorAll(".topic-items");
            for (let i = 0; i < questions.length; i++) {
                questions[i].classList.add("topic-items-active");
            }
        } else {
            plusMinus.innerText = "-";
            topic.querySelector(".subtopics").classList.add("subtopics-active");
            document.getElementById(nameID).classList.add("topic-items-active");
        }
    }
})();