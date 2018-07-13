
var keywords = [];
var grid;
var gridName = '.grid';
var current_sorting_scheme = "None";

$(window).load(function () {

    //handling clicks
    $('body').on('click', function (e) {
        handleClick(e);
    });

    //the click-able objects
    $('#keywords ul li').each(function(){
        keywords.push($(this).text());
    });
    console.log(keywords);


    headerNames = [];
    $(gridName + ' .item').each(function(){
        var text = this.getElementsByClassName('sortingAndFiltering')[0].textContent;
        var textSplit = text.split(';');
        console.log(textSplit);
        for(var i = 0; i < textSplit.length; i++) {
            if(textSplit[i] === "")
            {
                continue;
            }
            var data_str = (textSplit[i].split(':')[1]).split(',')[0];
            if(headerNames.indexOf(data_str) === -1) {
                headerNames.push(data_str);
                $(gridName).append("<div class='item' name='header' style='width: 100%;'><h2 style='margin: 0; background: white;'>"+ data_str +"</h2><div class='sortingAndFiltering' style ='display:none'>" + textSplit[i] + "</div><div class='Date' style='display:none'>"+ (Number.MAX_SAFE_INTEGER) +"</div></div>");
            }
        }
    });

    $grid = $(gridName).isotope(
    {
        //get the sorting data
        getSortData: {
            sorting_scheme: function (itemElem){
                return sortBySortingScheme(itemElem);
            },
            date: function (itemElem){
                return sortByDate(itemElem)
            }
        },
        filter: filterByFilteringScheme,
    });

});

function filterByFilteringScheme()
{
    var text = this.getElementsByClassName('sortingAndFiltering')[0].textContent;
    var textSplit = text.split(';');
    for(var i = 0; i < textSplit.length; i++)
    {
        var key = textSplit[i].split(':')[0];
        if(key === current_sorting_scheme)
        {
            return true;
        }
    }
    return false;
}

//sorts based on the 'sorting scheme'
function sortBySortingScheme (itemElem)
{
    var text = itemElem.getElementsByClassName('sortingAndFiltering')[0].textContent;
    console.log(text);
    //split by ';' --> we assume that this character splits between sorting entries.
    var textSplit = text.split(';');
    //get the line with the correct info (search through the lines of text for a key matching the sorting scheme
    var correct_line = "";
    for(var i = 0; i < textSplit.length; i++)
    {
        var key = textSplit[i].split(':')[0];
        if(key === current_sorting_scheme)
        {
            correct_line = textSplit[i];
        }
    }

    //if we found the right data
    if(correct_line !== "")
    {
        var parsing= (correct_line.split(':')[1]).split(',')[1];
        var data_str = correct_line.split(':')[1].split(',')[0];

        var data;
        if(parsing === "int")
        {
            data = parseInt(data_str);
        }
        else
        {
            data = data_str;
        }

        return data;
    }

    //otherwise, don't sort, since we have nothing to sort by.
    return "";
}

//sorts based on the date
function sortByDate(itemElem)
{
    var date_str = itemElem.getElementsByClassName('Date')[0].textContent;
    return parseInt(date_str) * -1;
}

function handleClick(e)
{
    if(isKeyword(e))
    {
        //assign the sorting scheme
        current_sorting_scheme = $(e.target).text();
        $grid.isotope('option',
        {
            //get the sorting data
            getSortData: {
                sorting_scheme: function (itemElem){
                    return sortBySortingScheme(itemElem);
                },
                date: function (itemElem){
                    return sortByDate(itemElem)
                }
            },
            filter: filterByFilteringScheme
        });

        console.log(current_sorting_scheme);
        //sort, first by sorting scheme and then by date
        $grid.isotope('updateSortData').isotope();
        $grid.isotope({ sortBy : ['sorting_scheme', 'date']});
    }
    else
    {
        $grid.isotope({ filter: '*'});
    }
}

function isKeyword(e)
{
    if($(e.target) && $(e.target).text())
    {
        for (var i = 0; i < keywords.length; i++)
        {
            if($(e.target).text() === keywords[i])
            {
                return true;
            }
        }
    }
    return false;
}