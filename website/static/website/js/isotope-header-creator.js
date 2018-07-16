$(window).load(function () {
    //get these properties from HTML, throw exceptions if we can't find them.
    var gridName = getAttribute($(isotope_data_container).text(), "gridName");
    var headerStyle = getAttribute($(isotope_data_container).text(), "headerStyle");
    var headerClass = getAttribute($(isotope_data_container).text(), "headerClass");

    if(gridName === null){
        throw "gridName property could not be found in isotope_data_container! Please add the gridName property!";
    }
    if(headerStyle === null){
        throw "headerStyle property could not be found in isotope_data_container! Please add the headerStyle property!";
    }
    if(headerClass === null){
        throw "headerClass property could not be found in isotope_data_container! Please add the headerClass property!";
    }

    var headerNames = [];
    //go through each item in the grid
    $(gridName + ' .item').each(function(){
        var sortFilterDataContainer = getAttribute($(isotope_data_container).text(), "isotopeFilterSortData");
        console.log("header creation: " + sortFilterDataContainer);

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
            if(headerNames.indexOf(textSplit[i]) === -1) {
                headerNames.push(textSplit[i]);
                //really long html insertion to properly make header.
                $(gridName).append("<div class='item' name='header' style='width: 100%; height: 50px; background: white;'><" + headerClass + " style="
                + headerStyle + ">"+ data +"</" + headerClass + "><div class=" + sortFilterDataContainer.substr(1, sortFilterDataContainer.length) + " style ='display:none'>"
                + textSplit[i] + "</div><div class='Date' style='display:none'>"+ (Number.MAX_SAFE_INTEGER) +"</div></div>");
            }
        }
    });
});