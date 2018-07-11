
var keywords = [];
var grid;
$(window).load(function () {
    $grid = $('.grid').isotope({});

    $('body').on('click', function (e) {
        handleClick(e);
    });

    $('#keywords ul li').each(function(){
        keywords.push($(this).text());
    });

    console.log(keywords);

});


function handleClick(e)
{
    if(isKeyword(e))
    {
        var filter = getFilter($(e.target).text());
        console.log(filter);
        $grid.isotope({ filter: filter});
    }
    else
    {
        $grid.isotope({ filter: '*'});
    }
}


function getFilter(keyword)
{
    return "." + keyword.replace(" ", "-").replace("/", "-");
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
