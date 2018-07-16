/*
 * Isotope sorting. Sorts by properties listed in the "sortingKeywordContainer"
 * Expects properties in the sortingKeywordContainer to have a "sort-ascending" attribute (set to true or false)
 * Expects data in the "sortFilterDataContainer" to be of the form "<Property>(<data>,<datatype>)"
 * E.g. Year(2018,int)Project(Sidewalk,str)
 * possible datatypes are "int", "str", and "float"
 */

// the property by which we're sorting
var sortingScheme = "None";
var $grid;

// function to initialize sorting
function isotopeSortInit() {
    // set the properties of the grid
    $grid = $(gridName).isotope({
        // get the sorting data
        getSortData: {
            sorting_scheme: function (itemElem) {
                return sortBySortingScheme(itemElem);
            },
            date: function (itemElem) {
                return sortByDate(itemElem)
            }
        },

        // get our current scheme for sorting
        sortAscending: {
            // check if we need to sort in ascending order or not.
            sorting_scheme: getIsPropertyAscending(sortingKeywordContainer, sortingScheme),
            date: false
        },
    });
}

// sorts based on the 'sorting scheme'
function sortBySortingScheme (itemElem)
{
    // get the value of the property that we're sorting by.
    return getValueOfProperty($(itemElem).find(sortFilterDataContainer)[0].textContent, sortingScheme);
}

// sorts based on the date (reverse chronological)
function sortByDate(itemElem)
{
    var date_str = $(itemElem).find('.Date')[0].textContent;
    return parseInt(date_str);
}

// handles click when called
function handleSortingClick(e){
    // get the text
    var text = $(e.target).attr("name");

    // check if the text is in the sorting keyword container
    if(isTextInContainer(sortingKeywordContainer, text))
    {
        // if it is, then set the sorting scheme and the grid settings
        sortingScheme = text;
        $grid.isotope('option',
        {
            // get the sorting data
            getSortData: {
                sorting_scheme: function (itemElem) {
                    return sortBySortingScheme(itemElem);
                },
                date: function (itemElem) {
                    return sortByDate(itemElem)
                }
            },

            sortAscending: {
                // check if we need to sort in ascending order or not.
                sorting_scheme: getIsPropertyAscending(sortingKeywordContainer, sortingScheme),
                date: false
            },
        });

        // update sorting data and sort
        $grid.isotope('updateSortData').isotope();
        $grid.isotope({ sortBy : ['sorting_scheme', 'date']});
    }
}

