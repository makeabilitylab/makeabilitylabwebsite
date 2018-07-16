/*
 * Filter bar that is compatible with isotope
 * Handles clicks, calls sorting and filtering functions if applicable
 * Generates filters on top of the ones specified in HTML using sort-filter data container
 */


var filterKeywords = [];
var filterNames = [];
function isotopeFilterBarInit(){
    // start the sidebar container
    $(sideBarContainer).fixedSideBar();

    $(sideBarContainer + ' li a').each(function(){
        // set the name attribute to the text of the element if the name attribute doesn't exist.
        var attr = $(this).attr("name");
        if(typeof attr === typeof undefined || attr === false) {
            $(this).attr("name", $(this).text());
        }

        // set the style so that we get the cursor
        $(this).attr("style", 'cursor: pointer;');

        //  put this into filterKeywords
        filterKeywords.push($(this).attr("name"));
    });

    //  handle clicks on the sidebar
    $(sideBarContainer).on('click', function (e) {
        handleFilterBarClick(e)
    });


    //  go through each item in the grid
    $(gridName + ' .item').each(function(){
        // get the types of headers from categories, split by ')'
        var text = $(this).find(sortFilterDataContainer)[0].textContent;
        var textSplit = text.split(')');
        // go through textSplit, only create headers that are unique and not empty
        for(var i = 0; i < textSplit.length; i++) {
            if(textSplit[i] === "") {
                continue;
            }
            var data = textSplit[i].split('(')[1].split(',')[0];
            if(filterNames.indexOf(textSplit[i].split('(')[0] + ";" + data) === -1) {
                filterNames.push(textSplit[i].split('(')[0] + ";" + data);
            }
        }
    });
}

// handles the onclick for filter bar
function handleFilterBarClick(e)
{
    // get our text
    var text = $(e.target).attr("name");

    // scroll up to
    $("html, body").animate({ scrollTop: 175 }, 1000);

    if(typeof handleFilteringClick !== typeof undefined){
        handleFilteringClick(e);
    }
    if(typeof handleSortingClick !== typeof undefined) {
        handleSortingClick(e);
    }

    if(filterKeywords.indexOf(text) > -1) {
        var filter_keywords_to_remove = $(filteringKeywordContainer).find('.added-filter-keywords');
        for(var i = 0; i < filter_keywords_to_remove.length; i++) {
            filter_keywords_to_remove[i].remove();
        }

        var numFilterMatches = 0;
        for(var i = 0; i < filterNames.length; i++) {
            if(filterNames[i].indexOf(text) !== -1) {
                numFilterMatches++;
            }
        }

        if(numFilterMatches > 0) {
            $(filteringKeywordContainer).append("<h1 class='added-filter-keywords'>" + text + "</h1>");
        }

        for(var i = 0; i < filterNames.length; i++) {
            if(filterNames[i].indexOf(text) !== -1) {
                 $(filteringKeywordContainer).append("<li class='added-filter-keywords' style='list-style-type:none;cursor:pointer;'><a name='"+ filterNames[i] +"'>" + filterNames[i].split(';')[1] + "</a></li>")
            }
        }
        if(numFilterMatches > 0) {
            $(filteringKeywordContainer).append("<li class='added-filter-keywords' style='list-style-type:none;cursor:pointer;'><a name='" + text + "'>all</a></li>");
        }
    }
}