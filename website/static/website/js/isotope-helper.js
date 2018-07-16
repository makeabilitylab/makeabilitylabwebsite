var isotope_data_container = '#isotope_data_container';

$(window).load(function () {
    $('#fixed-side-bar').fixedSideBar();
});

function getAttribute(text, attribute){
    var attributeLine = getAttributeLine(text, attribute);
    if(attributeLine === null)
    {
        return null;
    }
    return getParsedData(attributeLine);
}

//gets the line of data that has the attribute
function getAttributeLine(text, attribute){
    var dataSplit = text.split(')');
    var attribute_lower = attribute.toLowerCase();
    for(var i = 0; i < dataSplit.length; i++){
        if(dataSplit[i] !== "" && dataSplit[i].split('(')[0].toLowerCase() === attribute_lower){
            return dataSplit[i];
        }
    }
    console.log("returning null");
    return null;
}

function getIsAscending(text, attribute){
    return getIsAscending(getAttributeLine(text, attribute));
}

function getIsAscending(str){
    return (str.split('(')[1].split(',')[2]).toLowerCase() === "true";
}

function isKeyword(keywordContainer, text)
{
    var keywords = [];
    $(keywordContainer + ' a').each(function(){
        keywords.push($(this).attr("name"));
    });

    for (var i = 0; i < keywords.length; i++)
    {
        if(text === keywords[i])
        {
            return true;
        }
    }
    return false;
}

function getParsedData(str)
{
    if(str === null)
    {
        throw "cannot parse, string is null";
    }
    var parsing = str.split('(')[1].split(',')[1];
    var data = str.split('(')[1].split(',')[0];
    data = data.trim();
    if(parsing === "int")
    {
        return parseInt(data);
    }
    if(parsing === "float")
    {
        return parseFloat(data);
    }
    if(parsing === "str")
    {
        return data;
    }
    throw "the parse component (after the comma) of " + str + " is not int, float, or str.";
}
