/*
 * Isotope filtering. Sorts by properties listed in the "filteringKeywordContainer"
 * Expects data in the "sortFilterDataContainer" to be of the form "<Property>(<data>,<datatype>)" or "<Property>()"
 * Multiple properties can be in the same line
 * E.g. Year(2018,int)Accessibility()Project(Sidewalk,str)
 * possible datatypes are "int", "str", and "float"
 */

// the property by which we're filtering.
// e.x. "None", "Year", "Year;2018", "Project;Sidewalk"
var filteringScheme = "none";

// initialization for filtering
function isotopeFilterInit() {
    $($(currentIsotopeProperties['gridName'])).isotope({
        filter: filterByFilteringScheme,
    });
}

// filters by our current scheme
function filterByFilteringScheme() {
    // "none" is special case, everything else is normal
    if(filteringScheme.toLowerCase() === "none") {
        // filter out only the headers
        console.log($(this).attr("name"));
        return $(this).attr("name") !== "header";
    }

    // check if we have the property, if not return false.
    if(!hasProperty($(this).find(currentIsotopeProperties['sortFilterDataContainer'])[0].textContent, filteringScheme.split('(')[0])) {
        return false;
    }

    // get filterable data
    var data = getValueOfProperty($(this).find(currentIsotopeProperties['sortFilterDataContainer'])[0].textContent, filteringScheme.split('(')[0]);
    console.log("filtering data " + data);

    // if data is null, then return false, otherwise check if the data is equal to the filteringScheme or if the filtering scheme doesn't contain data.
    return (filteringScheme.indexOf('(') === -1 || (parsePropertyValue(filteringScheme) + "").trim() === (data + "").trim());
}

// handles the filter click
function handleFilteringClick(e) {
    // get the text
    var text = $(e.target).attr("name");
    //console.log(text);
    // check if text is in the filtering container
    if(isTextInContainer(currentIsotopeProperties['filteringKeywordContainer'], text)) {
        // set the filtering scheme, set the grid settings
        filteringScheme = text;
        //console.log("filterscheme" + filteringScheme);
        $($(currentIsotopeProperties['gridName'])).isotope({
            filter: filterByFilteringScheme,
        });
    }
}