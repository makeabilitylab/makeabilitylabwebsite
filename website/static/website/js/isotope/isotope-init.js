/*
 * Initializes grid for isotope, gets data from #isotope_data_container to set up isotope filtering/sorting logic.
 * Currently, it only supports one grid per page.
 * Expects properties to be present in #isotope_data_container in the form "<Property>(<value>,<valuetype>)" E.g. "gridName(.grid,str)"
 * possible datatypes are "int", "str", and "float"
 * Not all properties below need to be added, however, those required by the isotope sources being used must be added.
 * Contains helper functions for other filtering/sorting related logic.
 */

var isotope_data_container_class = '.isotope_data_container';

var allIsotopeProperties = [];

// get all of these properties from the isotope data container
var currentIsotopeProperties = {
    gridName:null,
    sortFilterDataContainer:null,
    headerStyle:null,
    headerClass:null,
    headerStyle:null,
    filteringKeywordContainer:null,
    sortingKeywordContainer:null,
    sideBarContainer:null,
    scrollTop:0,
};

$(window).load(function () {

    // get all the properties, throw errors if we can't find them. Call initialization functions for other isotopes if they exist.
    $('body ' + isotope_data_container_class).each(function() {
        var isotopeProperties = {};
        Object.assign(isotopeProperties, currentIsotopeProperties);
        isotopeProperties['gridName'] = getValueOfProperty($(this).text(), "gridName");
        isotopeProperties['sortFilterDataContainer'] = getValueOfProperty($(this).text(), "sortFilterContainer");
        if (isotopeProperties['gridName'] === null) {
            throw "gridName property could not be found in isotope_data_container! Please add the gridName property!";
        }
        if (isotopeProperties['sortFilterDataContainer'] === null) {
            throw "sortFilterContainer property could not be found in isotope_data_container! Please add the sortFilterContainer property!";
        }
        if (typeof isotopeHeaderInit !== typeof undefined) {
            isotopeProperties['headerStyle'] = getValueOfProperty($(this).text(), "headerStyle");
            isotopeProperties['headerClass'] = getValueOfProperty($(this).text(), "headerClass");
            if (isotopeProperties['headerStyle'] === null) {
                throw "headerStyle property could not be found in isotope_data_container! Please add the headerStyle property!";
            }
            if (isotopeProperties['headerClass'] === null) {
                throw "headerClass property could not be found in isotope_data_container! Please add the headerClass property!";
            }
        }
        if (typeof isotopeFilterInit !== typeof undefined) {
            isotopeProperties['filteringKeywordContainer'] = getValueOfProperty($(this).text(), "filteringKeywordContainer");
            if (isotopeProperties['filteringKeywordContainer'] === null) {
                throw "filteringKeywordContainer property could not be found in isotope_data_container! Please add the filteringKeywordContainer property!";
            }
        }
        if (typeof isotopeSortInit !== typeof undefined) {
            isotopeProperties['sortingKeywordContainer'] = getValueOfProperty($(this).text(), "sortingKeywordContainer");
            if (isotopeProperties['sortingKeywordContainer'] === null) {
                throw "sortingKeywordContainer property could not be found in isotope_data_container! Please add the sortingKeywordContainer property!";
            }
        }
        if (typeof isotopeFilterBarInit !== typeof undefined) {
            isotopeProperties['sideBarContainer'] = getValueOfProperty($(this).text(), "sideBarContainer");
            isotopeProperties['scrollTop'] = getValueOfProperty($(this).text(), "scrollTop");
            if (isotopeProperties['scrollTop'] === null) {
                throw "scrollTop property could not be found in isotope_data_container! Please add the scrollTop property!";
            }
            if (isotopeProperties['sideBarContainer'] === null) {
                throw "sideBarContainer property could not be found in isotope_data_container! Please add the sideBarContainer property!";
            }
        }
        // set layout mode to fit rows.
        $(isotopeProperties['gridName']).isotope({
            layoutMode: 'fitRows'
        });

        console.log(allIsotopeProperties.length);
        allIsotopeProperties.push(isotopeProperties);
    });




    for(var i = 0; i < allIsotopeProperties.length; i++) (function(i){
        currentIsotopeProperties = allIsotopeProperties[i];
        init();
        $(currentIsotopeProperties['sideBarContainer'] + ' a').each(function(idx, item){
            $(item).on('click', function (e) {
                if (currentIsotopeProperties !== allIsotopeProperties[i]) {
                    currentIsotopeProperties = allIsotopeProperties[i];
                    console.log("handling click");
                    init();
                }

                console.log("finished init, moving to filter bar");
                handleFilterBarClick(e);
            });
        });
    })(i);
});

function init(){
    if (typeof isotopeHeaderInit !== typeof undefined) {
        isotopeHeaderInit();
    }
    if (typeof isotopeFilterInit !== typeof undefined) {
        isotopeFilterInit();
    }
    if (typeof isotopeSortInit !== typeof undefined) {
        isotopeSortInit();
    }
    if (typeof isotopeFilterBarInit !== typeof undefined) {
        isotopeFilterBarInit();
    }
}


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