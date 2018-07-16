//filter out all headers at the start.
var filteringScheme = "None";

$(window).load(function () {
    $('body').on('click', function (e) {
        handleFilteringClick(e);
    });
    $(getAttribute($(isotope_data_container).text(), "gridName")).isotope({
        columnWidth: 100,
        rowGap: 100,
        itemSelector: '.item',
        layoutMode: 'fitRows',
        filter: filterByFilteringScheme,
    });
});

function filterByFilteringScheme()
{
    //none is special case, everything else is normal
    if(filteringScheme.toLowerCase() === "none")
    {
        //filter out the headers
        return $(this).attr("name") !== "header";
    }

    var className = getAttribute($(isotope_data_container).text(), "isotopeFilterSortData");

    className = className.substr(1,className.length);
    console.log($(this).attr("class") + " className " + className);
    //see if we can get the data about this filtering scheme
    var data = getAttribute(this.getElementsByClassName(className)[0].textContent, filteringScheme.split(';')[0]);
    //if data is null, then return false, otherwise check if the data is equal to the filteringScheme or if the filtering scheme doesn't contain data.
    return data !== null && (filteringScheme.indexOf(';') === -1 || filteringScheme.split(';')[1] === (data + ""));
}

function handleFilteringClick(e)
{
    //get the text, get the keyword container
    var text = $(e.target).text();
    var keywordContainer = getAttribute($(isotope_data_container).text(), "filteringKeywordContainer");
    if(isKeyword(keywordContainer, text))
    {
        filteringScheme = text;
        $(getAttribute($(isotope_data_container).text(), "gridName")).isotope({
            filter: filterByFilteringScheme,
        });
    }
}