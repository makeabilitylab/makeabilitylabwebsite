
var original_keywords = [];
var filterNames = [];
var filter_keywords_container;
$(window).load(function () {
    filter_keywords_container = getAttribute($(isotope_data_container).text(), "filteringKeywordContainer");
    $(filter_keywords_container + ' li a').each(function(){
        var attr = $(this).attr("name");
        if(typeof attr === typeof undefined || attr === false)
        {
            $(this).attr("name", $(this).text());
        }
        $(this).attr("style", 'cursor: pointer;');
        original_keywords.push($(this).attr("name"));
    });
    $(filter_keywords_container).on('click', function (e) {
        handleFilterBarClick(e)
    });


    //go through each item in the grid
    $(getAttribute($(isotope_data_container).text(), "gridName") + ' .item').each(function(){
        var sortFilterDataContainer = getAttribute($(isotope_data_container).text(), "isotopeFilterSortData");
        //get the types of headers from categories, split by ';'
        var text = $(this).find(sortFilterDataContainer)[0].textContent;
        var textSplit = text.split(')');
        //go through textSplit, only create headers that are unique and not "".
        for(var i = 0; i < textSplit.length; i++) {
            if(textSplit[i] === "")
            {
                continue;
            }
            var data = textSplit[i].split('(')[1].split(',')[0];
            if(filterNames.indexOf(textSplit[i].split('(')[0] + ";" + data) === -1) {
                filterNames.push(textSplit[i].split('(')[0] + ";" + data);
            }
        }
    });
});


function handleFilterBarClick(e)
{
    var text = $(e.target).attr("name");

    if(typeof handleFilteringClick !== undefined){
        handleFilteringClick(e);
    }
    if(typeof handleSortingClick !== undefined) {
        handleSortingClick(e);
    }

    if(original_keywords.indexOf(text) > -1)
    {
        var filter_keywords_to_remove = $(filter_keywords_container).find('.added-filter-keywords');
        for(var i = 0; i < filter_keywords_to_remove.length; i++)
        {
            filter_keywords_to_remove[i].remove();
        }
        if(text !== "None")
        {
            $(filter_keywords_container).append("<h1 class='added-filter-keywords'>" + text + "</h1>");
        }

        for(var i = 0; i < filterNames.length; i++)
        {
            if(filterNames[i].indexOf(text) !== -1)
            {
                 $(filter_keywords_container).append("<li class='added-filter-keywords' style='list-style-type:none;cursor:pointer;'><a name='"+ filterNames[i] +"'>" + filterNames[i].split(';')[1] + "</a></li>")
            }
        }

        if(text !== "None") {
            $(filter_keywords_container).append("<li class='added-filter-keywords' style='list-style-type:none;cursor:pointer;'><a name='" + text + "'>all</a></li>");
        }
    }
}