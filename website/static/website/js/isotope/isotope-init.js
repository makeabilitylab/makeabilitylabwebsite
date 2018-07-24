/*
 * Initializes grid for isotope, gets data from #isotope_data_container to set up isotope filtering/sorting logic.
 * Currently, it only supports one grid per page.
 * Expects properties to be present in #isotope_data_container in the form "<Property>(<value>,<valuetype>)" E.g. "gridName(.grid,str)"
 * possible datatypes are "int", "str", and "float"
 * Not all properties below need to be added, however, those required by the isotope sources being used must be added.
 * Contains helper functions for other filtering/sorting related logic.
 */


var isotope_data_container = '#isotope_data_container';

// get all of these properties from the isotope data container

// required always
var gridName;
var sortFilterDataContainer;

// required for header generation
var headerStyle;
var headerClass;

// required for filtering
var filteringKeywordContainer;
// required for sorting
var sortingKeywordContainer;

// required for the filter-bar
var sideBarContainer;
var scrollTop;

$(window).load(function () {
    // get all the properties, throw errors if we can't find them. Call initialization functions for other isotopes if they exist.
    gridName = getValueOfProperty($(isotope_data_container).text(), "gridName");
    sortFilterDataContainer = getValueOfProperty($(isotope_data_container).text(), "sortFilterContainer");
    if(gridName === null) {
        throw "gridName property could not be found in isotope_data_container! Please add the gridName property!";
    }
    if(sortFilterDataContainer === null) {
        throw "sortFilterContainer property could not be found in isotope_data_container! Please add the sortFilterContainer property!";
    }
    if(typeof isotopeHeaderInit !== typeof undefined) {
        headerStyle = getValueOfProperty($(isotope_data_container).text(), "headerStyle");
        headerClass = getValueOfProperty($(isotope_data_container).text(), "headerClass");
        if(headerStyle === null) {
            throw "headerStyle property could not be found in isotope_data_container! Please add the headerStyle property!";
        }
        if(headerClass === null) {
            throw "headerClass property could not be found in isotope_data_container! Please add the headerClass property!";
        }
        isotopeHeaderInit();
    }
    if(typeof isotopeFilterInit !== typeof undefined) {
        filteringKeywordContainer = getValueOfProperty($(isotope_data_container).text(), "filteringKeywordContainer");
        if(filteringKeywordContainer === null) {
            throw "filteringKeywordContainer property could not be found in isotope_data_container! Please add the filteringKeywordContainer property!";
        }
        isotopeFilterInit();
    }
    if(typeof isotopeSortInit !== typeof undefined) {
        sortingKeywordContainer = getValueOfProperty($(isotope_data_container).text(), "sortingKeywordContainer");
        if(sortingKeywordContainer === null) {
            throw "sortingKeywordContainer property could not be found in isotope_data_container! Please add the sortingKeywordContainer property!";
        }
        isotopeSortInit();
    }
    if(typeof isotopeFilterBarInit !== typeof undefined) {
        sideBarContainer = getValueOfProperty($(isotope_data_container).text(), "sideBarContainer");
        scrollTop = getValueOfProperty($(isotope_data_container).text(), "scrollTop");
        if (scrollTop === null) {
            throw "scrollTop property could not be found in isotope_data_container! Please add the scrollTop property!";
        }
        if (sideBarContainer === null) {
            throw "sideBarContainer property could not be found in isotope_data_container! Please add the sideBarContainer property!";
        }
        isotopeFilterBarInit();
    }

    // set layout mode to fit rows.
    $(gridName).isotope({
        layoutMode: 'fitRows'
    });
});

// gets value of a property
function getValueOfProperty(text, property){
    var propertyLine = getLineOfProperty(text, property);
    if(propertyLine === null) {
        return null;
    }
    return parsePropertyValue(propertyLine);
}

// checks if there is a property
function hasProperty(text, property){
    return getLineOfProperty(text, property) !== null;
}

// gets the line of data that has the property
function getLineOfProperty(text, property){
    var dataSplit = text.split(')');
    var property_lower = property.toLowerCase();
    for(var i = 0; i < dataSplit.length; i++){
        if(dataSplit[i].trim() !== "" && dataSplit[i].split('(')[0].toLowerCase().trim() === property_lower.trim()){
            return dataSplit[i].trim();
        }
    }
    console.log("returning null");
    return null;
}

// gets if a property is sorted in ascending order
function getIsPropertyAscending(property_container, property){
    var result = false;
    $(property_container + ' a').each(function(){
        if($(this).attr("name") === property){
            console.log(property);
            result = $(this).attr("sorting-order").toLowerCase().trim() === "true";
            return false;
        }
    });
    return result;
}


// returns if the text could be found in the container
// e.x. if the HTML is this: <div id="test"><a>test</a></div>
// then isTextInContainer(#test,test) -> true
function isTextInContainer(container, text) {
    var keywords = [];
    $(container + ' a').each(function(){
        keywords.push($(this).attr("name"));
    });

    for (var i = 0; i < keywords.length; i++) {
        if(text === keywords[i]) {
            return true;
        }
    }
    return false;
}

// takes in a single property, returns parsed value
// e.x. Project(Sidewalk,str,false -> Sidewalk
function parsePropertyValue(str) {
    if(str === null) {
        throw "cannot parse, string is null";
    }
    var parsing = str.split('(')[1].split(',')[1];
    var data = str.split('(')[1].split(',')[0];
    data = data.trim();
    if(parsing === "int") {
        return parseInt(data);
    }
    if(parsing === "float") {
        return parseFloat(data);
    }
    if(parsing === "str") {
        return data;
    }
    return null;
}