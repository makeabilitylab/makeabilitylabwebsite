/*
 * Dynamically creates headers from data in the "sortFilterDataContainer"
 * Expects data in the "sortFilterDataContainer" to be of the form "<Property>(<data>,<datatype>)"
 * possible datatypes are "int", "str", and "float"
 */

// initializes header creation
function isotopeHeaderInit() {
    var headerNames = [];

    // go through each item in the grid
    $(gridName + ' .item').each(function(){
        // get the types of headers from categories, split by ')'
        var text = $(this).find(sortFilterDataContainer)[0].textContent;
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
                $(gridName).append("<div class='item' name='header' style='width: 100%; height: 50px; background: white;'><" + headerClass + " style="
                + headerStyle + ">"+ data +"</" + headerClass + "><div class=" + sortFilterDataContainer.substr(1, sortFilterDataContainer.length) + " style ='display:none'>"
                + textSplit[i] + "</div><div class='Date' style='display:none'>"+ (Number.MAX_SAFE_INTEGER) +"</div></div>");
            }
        }
    });
}