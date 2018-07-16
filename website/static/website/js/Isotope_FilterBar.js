
var original_keywords = [];
var filterNames = [];
var current_added_elements = [];
var filter_keywords_container;
$(window).load(function () {
    filter_keywords_container = getAttribute($(isotope_data_container).textContent, "filteringKeywordContainer");
    $(filter_keywords_container + ' li a').each(function(){
        original_keywords.push($(this).text());
    });
    $(filter_keywords_container).on('click', function (e) {
        handleFilterBarClick(e)
    });

    var filterNames = [];
    //go through each item in the grid
    $(getAttribute($(isotope_data_container).textContent, "gridName") + ' .item').each(function(){
        var sortFilterDataContainer = getAttribute($(isotope_data_container).text(), "isotopeFilterSortData");
        //get the types of headers from categories, split by ';'
        var text = $(this).find(sortFilterDataContainer)[0].textContent;
        var textSplit = text.split(')');
        console.log(textSplit);
        //go through textSplit, only create headers that are unique and not "".
        for(var i = 0; i < textSplit.length; i++) {
            if(textSplit[i] === "")
            {
                continue;
            }
            var data = textSplit[i].split('(')[1].split(',')[0];
            if(filterNames.indexOf(data) === -1) {
                filterNames.push(data);
            }
        }
    });
});


function handleFilterBarClick(e)
{
    var text = $(e.target).text();
    $(filter_keywords_container).removeClass('.added-filter-keywords');
    if(text in original_keywords)
    {

    }
}