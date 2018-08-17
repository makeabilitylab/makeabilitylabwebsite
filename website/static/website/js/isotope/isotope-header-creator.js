/*
 * Dynamically creates headers from data in the "sortFilterDataContainer"
 * Expects data in the "sortFilterDataContainer" to be of the form "<Property>(<data>,<datatype>)"
 * possible datatypes are "int", "str", and "float"
 */

// initializes header creation
function isotopeHeaderInit() {
    var headerNames = [];

    // go through each item in the grid
    $(currentIsotopeProperties['gridName'] + ' .item').each(function(){
        // get the types of headers from categories, split by ')'
        var text = $(this).find($(currentIsotopeProperties['sortFilterDataContainer']))[0].textContent;
        var textSplit = text.split(')');

        // go through textSplit, only create headers that are unique and not empty.
        for(var i = 0; i < textSplit.length; i++) {
            if(textSplit[i] === "") {
                continue;
            }

            var data = textSplit[i].split('(')[1].split(',')[0];
            
            if(headerNames.indexOf(textSplit[i]) === -1) {
                headerNames.push(textSplit[i]);
                //  really long html insertion to properly make header.
                $(currentIsotopeProperties['gridName']).append(
                    //creating an item wrapper so that the header can be put in the grid
                    "<div class='item' name='header' style='width: 100%; height: 50px; background: white;'>" +
                        // making the visible header, putting in the data to be shown
                        "<" + currentIsotopeProperties['headerClass'] + " style=" + currentIsotopeProperties['headerStyle'] + ">" +
                            data +
                        "</" + currentIsotopeProperties['headerClass'] + ">" +

                        // making the sortFilterData container
                        "<div style='display:none' class=" + currentIsotopeProperties['sortFilterDataContainer'].substr(1, currentIsotopeProperties['sortFilterDataContainer'].length) + ">" +
                            textSplit[i] +
                        "</div>" +

                        // making the Date container (and setting the date to the max value so that the header is sorted first)
                        "<div class='Date' style='display:none'>" +
                            (Number.MAX_SAFE_INTEGER) +
                        "</div>" +
                    "</div>"
                );
            }
        }
    });
}