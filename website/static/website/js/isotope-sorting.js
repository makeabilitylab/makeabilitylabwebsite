var sortingScheme = "None";
var $grid;

$(window).load(function () {
    var gridName = getAttribute($(isotope_data_container).text(), "gridName");
    $grid = $(gridName).isotope({
        //get the sorting data
        getSortData: {
            sorting_scheme: function (itemElem) {
                return sortBySortingScheme(itemElem);
            },
            date: function (itemElem) {
                return sortByDate(itemElem)
            }
        },

        sortAscending: {

            //check if we need to sort in ascending order or not.
            sorting_scheme: false,
            date: false
        },
    });
});

//sorts based on the 'sorting scheme'
function sortBySortingScheme (itemElem)
{
    return getAttribute($(itemElem).find(getAttribute($(isotope_data_container).text(), "isotopeFilterSortData"))[0].textContent, sortingScheme);
}

//sorts based on the date (reverse chronological)
function sortByDate(itemElem)
{
    var date_str = $(itemElem).find('.Date')[0].textContent;
    return parseInt(date_str);
}

//handles click
function handleSortingClick(e){
    //get the text, get the keyword container
    var text = $(e.target).text();
    var keywordContainer = getAttribute($(isotope_data_container).text(), "sortingKeywordContainer");
    if(isKeyword(keywordContainer, text))
    {
        sortingScheme = text;
        $grid.isotope('option',
        {
            //get the sorting data
            getSortData: {
                sorting_scheme: function (itemElem) {
                    return sortBySortingScheme(itemElem);
                },
                date: function (itemElem) {
                    return sortByDate(itemElem)
                }
            },

            sortAscending: {
                //check if we need to sort in ascending order or not.
                sorting_scheme: false,
                date: false
            },
        });
        $grid.isotope('updateSortData').isotope();
        $grid.isotope({ sortBy : ['sorting_scheme', 'date']});
    }
}

