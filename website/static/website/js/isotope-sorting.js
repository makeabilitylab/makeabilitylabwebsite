var sortingScheme = "None";
var $grid;

$(window).load(function () {

    console.log("hello" + $(isotope_data_container).text());
    console.log(getAttribute($(isotope_data_container).text(), "gridName"));
    $('body').on('click', function (e) {
        handleSortingClick(e);
    });
    var gridName = getAttribute($(isotope_data_container).text(), "gridName");
    $grid = $(gridName).isotope({
        columnWidth: 100,
        rowGap: 100,
        itemSelector: '.item',
        layoutMode: 'fitRows',
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
    console.log($(gridName).find('.item')[0].textContent);
});

//sorts based on the 'sorting scheme'
function sortBySortingScheme (itemElem)
{
    return getAttribute($(itemElem).find(getAttribute($(isotope_data_container).text(), "isotopeFilterSortData"))[0].textContent, sortingScheme);
}

//sorts based on the date (reverse chronological)
function sortByDate(itemElem)
{
    console.log($(itemElem).attr("name"));
    var date_str = $(itemElem).find('.Date')[0].textContent;
    return parseInt(date_str);
}

//handles click
function handleSortingClick(e){
    //get the text, get the keyword container
    var text = $(e.target).text();
    console.log("HANDLING SORTING CLICK");
    var keywordContainer = getAttribute($(isotope_data_container).text(), "sortingKeywordContainer");
    if(isKeyword(keywordContainer, text))
    {
        console.log("here");
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

